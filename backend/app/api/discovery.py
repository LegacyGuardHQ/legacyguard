from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.discovery import (
    DISCOVERY_SCAN_STATUS_COMPLETE,
    DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS,
    DISCOVERY_SCAN_STATUS_FAILED,
    DISCOVERY_SCAN_STATUS_PENDING,
    DISCOVERY_SCAN_STATUS_RUNNING,
    DISCOVERY_SCAN_STATUS_VALUES,
    EVIDENCE_REVIEW_STATUS_CONFIRMED,
    EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
    EVIDENCE_REVIEW_STATUS_VALUES,
    DiscoveryScan,
    EvidenceFinding,
)
from app.models.discovery_asset_link import DiscoveryFindingAssetLink
from app.models.discovery_scan_document import DiscoveryScanDocument
from app.models.document import Document
from app.models.asset import Asset
from app.models.user import User
from app.schemas.discovery import (
    DiscoveryReportSummaryResponse,
    DiscoverySafeReportResponse,
    DiscoveryDashboardResponse,
    DiscoveryScanDocumentResponse,
    DiscoveryScanCreate,
    DiscoveryScanResponse,
    DiscoveryScanStatusResponse,
    DiscoveryScanSummaryResponse,
    EvidenceFindingResponse,
    EvidenceFindingDetailResponse,
    EvidenceFindingReviewRequest,
    ManualAssetConversionRequest,
    PaginatedDiscoveryScanResponse,
    PaginatedEvidenceFindingResponse,
)
from app.schemas.assets import AssetCreate, AssetDetailCreate, AssetResponse
from app.security.auth import get_current_user, get_db
from app.services.asset_creation import create_asset_record
from app.services.audit import log_event
from app.services.discovery_categories import DISCOVERY_CATEGORY_VALUES
from app.services.discovery_orchestrator import DiscoveryOrchestrationError, DiscoveryOrchestrator
from app.services.discovery_reports import DiscoveryReportService

router = APIRouter(prefix="/discovery", tags=["discovery"])
discovery_orchestrator = DiscoveryOrchestrator()
discovery_report_service = DiscoveryReportService()


def _scan_response(scan: DiscoveryScan) -> DiscoveryScanResponse:
    return DiscoveryScanResponse(scan_id=scan.id, status=scan.status, created_at=scan.created_at)


def _derive_lifecycle_state(status: str) -> str:
    if status == DISCOVERY_SCAN_STATUS_PENDING:
        return "QUEUED"
    if status == DISCOVERY_SCAN_STATUS_RUNNING:
        return "RUNNING"
    if status == DISCOVERY_SCAN_STATUS_COMPLETE:
        return "COMPLETED"
    if status == DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS:
        return "COMPLETED_WITH_WARNINGS"
    if status == DISCOVERY_SCAN_STATUS_FAILED:
        return "FAILED"
    return "QUEUED"


def _get_scan_recovery_metadata(db: Session, *, scan: DiscoveryScan, user_id: str) -> tuple[bool, datetime | None]:
    recovery_audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.event_type == "discovery_started",
            AuditLog.details == "Discovery scan recovered from stale running state",
        )
        .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
        .all()
    )
    for audit_entry in recovery_audit:
        metadata = audit_entry.event_metadata or {}
        if metadata.get("scan_id") == scan.id:
            return True, audit_entry.timestamp
    return False, None


def _get_scan_retry_count(db: Session, *, scan: DiscoveryScan, user_id: str) -> int:
    recovery_audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.event_type == "discovery_started",
            AuditLog.details == "Discovery scan recovered from stale running state",
        )
        .all()
    )
    retry_count = 0
    for audit_entry in recovery_audit:
        metadata = audit_entry.event_metadata or {}
        if metadata.get("scan_id") == scan.id:
            retry_count += 1
    return retry_count


def _get_scan_failure_metadata(db: Session, *, scan: DiscoveryScan, user_id: str) -> tuple[int, datetime | None]:
    failure_audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.event_type == "discovery_failed",
            AuditLog.details == "Discovery scan failed",
        )
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .all()
    )
    failure_count = 0
    last_failure_at: datetime | None = None
    for audit_entry in failure_audit:
        metadata = audit_entry.event_metadata or {}
        if metadata.get("scan_id") == scan.id:
            failure_count += 1
            if last_failure_at is None:
                last_failure_at = audit_entry.timestamp
    return failure_count, last_failure_at


def _derive_processing_outcome(status: str, *, recovered_from_stale: bool) -> tuple[str, str]:
    if recovered_from_stale and status in {DISCOVERY_SCAN_STATUS_COMPLETE, DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS}:
        return "RECOVERED_AND_COMPLETED", "Recovered and completed"
    if recovered_from_stale:
        return "RECOVERED", "Recovered from a stale running state"
    if status == DISCOVERY_SCAN_STATUS_PENDING:
        return "QUEUED", "Queued for processing"
    if status == DISCOVERY_SCAN_STATUS_RUNNING:
        return "IN_PROGRESS", "Processing is active"
    if status == DISCOVERY_SCAN_STATUS_COMPLETE:
        return "COMPLETED", "Completed successfully"
    if status == DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS:
        return "COMPLETED_WITH_WARNINGS", "Completed with warnings"
    if status == DISCOVERY_SCAN_STATUS_FAILED:
        return "FAILED", "Failed"
    return "IN_PROGRESS", "Processing is active"


def _derive_background_job_state(
    status: str,
    *,
    retry_count: int,
    failure_count: int,
) -> tuple[str, str]:
    if status == DISCOVERY_SCAN_STATUS_FAILED:
        return "FAILED", "Background processing failed"
    if status in {DISCOVERY_SCAN_STATUS_COMPLETE, DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS}:
        return "COMPLETED", "Background processing completed"
    if retry_count > 0:
        return "RETRYING", "Retrying background processing"
    if status == DISCOVERY_SCAN_STATUS_RUNNING:
        return "RUNNING", "Background processing is active"
    if failure_count > 0:
        return "RETRYING", "Retrying background processing"
    return "QUEUED", "Queued for background processing"


def _scan_status_response(db: Session, scan: DiscoveryScan, user_id: str) -> DiscoveryScanStatusResponse:
    recovered_from_stale, recovered_at = _get_scan_recovery_metadata(db, scan=scan, user_id=user_id)
    retry_count = _get_scan_retry_count(db, scan=scan, user_id=user_id)
    failure_count, last_failure_at = _get_scan_failure_metadata(db, scan=scan, user_id=user_id)
    processing_outcome, processing_outcome_message = _derive_processing_outcome(
        scan.status,
        recovered_from_stale=recovered_from_stale,
    )
    background_job_state, background_job_message = _derive_background_job_state(
        scan.status,
        retry_count=retry_count,
        failure_count=failure_count,
    )
    return DiscoveryScanStatusResponse(
        scan_id=scan.id,
        status=scan.status,
        documents_processed=scan.documents_processed,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
        lifecycle_state=_derive_lifecycle_state(scan.status),
        recovered_from_stale=recovered_from_stale,
        recovered_at=recovered_at,
        processing_outcome=processing_outcome,
        processing_outcome_message=processing_outcome_message,
        background_job_state=background_job_state,
        background_job_message=background_job_message,
        retry_count=retry_count,
        failure_count=failure_count,
        last_failure_at=last_failure_at,
    )


def _scan_summary_response(scan: DiscoveryScan) -> DiscoveryScanSummaryResponse:
    return DiscoveryScanSummaryResponse(
        scan_id=scan.id,
        status=scan.status,
        documents_processed=scan.documents_processed,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
    )


def _finding_response(finding: EvidenceFinding) -> EvidenceFindingResponse:
    return EvidenceFindingResponse(
        finding_id=finding.id,
        category=finding.category,
        confidence_score=finding.confidence_score,
        review_status=finding.review_status,
        created_at=finding.created_at,
    )


def _finding_detail_response(finding: EvidenceFinding, document: Document) -> EvidenceFindingDetailResponse:
    return EvidenceFindingDetailResponse(
        **_finding_response(finding).model_dump(),
        scan_id=finding.scan_id,
        document_id=document.id,
        document_name=document.document_name,
        document_type=document.document_type,
    )





def _asset_response(asset: Asset) -> AssetResponse:
    detail = asset.details
    detail_response = None
    if detail is not None:
        from app.schemas.assets import AssetDetailResponse

        detail_response = AssetDetailResponse(
            account_number=detail.get_decrypted_value("account_number_encrypted"),
            policy_number=detail.get_decrypted_value("policy_number_encrypted"),
            notes=detail.get_decrypted_value("notes_encrypted"),
            claim_instructions=detail.get_decrypted_value("claim_instructions_encrypted"),
        )
    return AssetResponse(
        id=asset.id,
        asset_category=asset.asset_category,
        asset_name=asset.asset_name,
        institution=asset.institution,
        description=asset.description,
        estimated_value=asset.estimated_value,
        ownership_type=asset.ownership_type,
        status=asset.status,
        is_verified=asset.is_verified,
        verification_status=asset.verification_status,
        verified_at=asset.verified_at,
        archived_at=asset.archived_at,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        details=detail_response,
    )


def _review_event_type(old_status: str, new_status: str) -> str:
    if new_status == EVIDENCE_REVIEW_STATUS_PENDING_REVIEW:
        return "finding_review_reopened"
    if old_status == EVIDENCE_REVIEW_STATUS_PENDING_REVIEW:
        return "finding_reviewed"
    return "finding_review_corrected"


def _get_owned_scan(db: Session, scan_id: str, user_id: str) -> DiscoveryScan:
    scan = db.query(DiscoveryScan).filter(DiscoveryScan.id == scan_id, DiscoveryScan.user_id == user_id).first()
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery scan not found")
    return scan


def _get_owned_finding(db: Session, finding_id: str, user_id: str) -> EvidenceFinding:
    finding = (
        db.query(EvidenceFinding)
        .join(DiscoveryScan, EvidenceFinding.scan_id == DiscoveryScan.id)
        .filter(EvidenceFinding.id == finding_id, DiscoveryScan.user_id == user_id)
        .first()
    )
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence finding not found")
    return finding


@router.post("/scans", response_model=DiscoveryScanResponse, status_code=status.HTTP_201_CREATED)
def create_discovery_scan(
    payload: DiscoveryScanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiscoveryScanResponse:
    try:
        scan = discovery_orchestrator.run_scan(db, user_id=current_user.id, document_ids=payload.document_ids)
    except DiscoveryOrchestrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discovery scan failed") from exc
    return _scan_response(scan)


@router.get("/dashboard", response_model=DiscoveryDashboardResponse)
def get_discovery_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiscoveryDashboardResponse:
    scan_status_rows = (
        db.query(DiscoveryScan.status, func.count(DiscoveryScan.id))
        .filter(DiscoveryScan.user_id == current_user.id)
        .group_by(DiscoveryScan.status)
        .all()
    )
    scans_by_status = {scan_status: 0 for scan_status in DISCOVERY_SCAN_STATUS_VALUES}
    for scan_status, count in scan_status_rows:
        if scan_status not in scans_by_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Discovery dashboard contains an unsupported scan status",
            )
        scans_by_status[scan_status] = count

    review_status_rows = (
        db.query(EvidenceFinding.review_status, func.count(EvidenceFinding.id))
        .join(DiscoveryScan, EvidenceFinding.scan_id == DiscoveryScan.id)
        .filter(DiscoveryScan.user_id == current_user.id)
        .group_by(EvidenceFinding.review_status)
        .all()
    )
    findings_by_review_status = {
        review_status: 0 for review_status in EVIDENCE_REVIEW_STATUS_VALUES
    }
    for review_status, count in review_status_rows:
        if review_status not in findings_by_review_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Discovery dashboard contains an unsupported review status",
            )
        findings_by_review_status[review_status] = count

    category_rows = (
        db.query(EvidenceFinding.category, func.count(EvidenceFinding.id))
        .join(DiscoveryScan, EvidenceFinding.scan_id == DiscoveryScan.id)
        .filter(DiscoveryScan.user_id == current_user.id)
        .group_by(EvidenceFinding.category)
        .order_by(EvidenceFinding.category.asc())
        .all()
    )
    recent_scans = (
        db.query(DiscoveryScan)
        .filter(DiscoveryScan.user_id == current_user.id)
        .order_by(DiscoveryScan.created_at.desc(), DiscoveryScan.id.desc())
        .limit(5)
        .all()
    )
    return DiscoveryDashboardResponse(
        total_scans=sum(scans_by_status.values()),
        scans_by_status=scans_by_status,
        total_findings=sum(findings_by_review_status.values()),
        pending_reviews=findings_by_review_status[EVIDENCE_REVIEW_STATUS_PENDING_REVIEW],
        findings_by_category={category: count for category, count in category_rows},
        findings_by_review_status=findings_by_review_status,
        recent_scans=[_scan_summary_response(scan) for scan in recent_scans],
    )


@router.get("/scans", response_model=PaginatedDiscoveryScanResponse)
def list_discovery_scans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedDiscoveryScanResponse:
    owned_query = db.query(DiscoveryScan).filter(DiscoveryScan.user_id == current_user.id)
    total_count = owned_query.count()
    scans = (
        owned_query
        .order_by(DiscoveryScan.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = (total_count + page_size - 1) // page_size if total_count else 0
    return PaginatedDiscoveryScanResponse(
        items=[_scan_summary_response(scan) for scan in scans],
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/scans/{scan_id}", response_model=DiscoveryScanStatusResponse)
def get_discovery_scan_status(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiscoveryScanStatusResponse:
    scan = _get_owned_scan(db, scan_id, current_user.id)
    return _scan_status_response(db, scan, current_user.id)


@router.get("/scans/{scan_id}/summary", response_model=DiscoveryReportSummaryResponse)
def get_discovery_scan_summary(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiscoveryReportSummaryResponse:
    scan = _get_owned_scan(db, scan_id, current_user.id)
    summary = discovery_report_service.build_summary(db, scan)
    return DiscoveryReportSummaryResponse(
        scan_id=summary.scan_id,
        status=summary.status,
        total_findings=summary.total_findings,
        categories=summary.categories,
        review_statuses=summary.review_statuses,
    )


@router.get("/scans/{scan_id}/report", response_model=DiscoverySafeReportResponse)
def get_discovery_scan_report(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiscoverySafeReportResponse:
    scan = _get_owned_scan(db, scan_id, current_user.id)
    payload = discovery_report_service.build_safe_export(db, scan)
    return DiscoverySafeReportResponse(**payload)


@router.get("/scans/{scan_id}/findings", response_model=PaginatedEvidenceFindingResponse)
def list_discovery_findings(
    scan_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    review_status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedEvidenceFindingResponse:
    scan = _get_owned_scan(db, scan_id, current_user.id)
    if review_status is not None and review_status not in EVIDENCE_REVIEW_STATUS_VALUES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported review status")

    owned_query = db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == scan.id)
    if review_status is not None:
        owned_query = owned_query.filter(EvidenceFinding.review_status == review_status)

    total_count = owned_query.count()
    findings = (
        owned_query
        .order_by(EvidenceFinding.created_at.asc(), EvidenceFinding.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = (total_count + page_size - 1) // page_size if total_count else 0
    return PaginatedEvidenceFindingResponse(
        items=[_finding_response(finding) for finding in findings],
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/scans/{scan_id}/documents", response_model=list[DiscoveryScanDocumentResponse])
def list_discovery_scan_documents(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DiscoveryScanDocumentResponse]:
    scan = _get_owned_scan(db, scan_id, current_user.id)
    rows = (
        db.query(DiscoveryScanDocument, Document)
        .join(Document, DiscoveryScanDocument.document_id == Document.id)
        .filter(
            DiscoveryScanDocument.scan_id == scan.id,
            Document.user_id == current_user.id,
        )
        .order_by(DiscoveryScanDocument.created_at.asc(), DiscoveryScanDocument.id.asc())
        .all()
    )
    return [
        DiscoveryScanDocumentResponse(
            document_id=document.id,
            document_name=document.document_name,
            document_type=document.document_type,
            status=tracking.status,
            warning_code=tracking.warning_code,
            created_at=tracking.created_at,
        )
        for tracking, document in rows
    ]


@router.get("/findings/review-queue", response_model=PaginatedEvidenceFindingResponse)
def list_discovery_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    review_status: str = Query(EVIDENCE_REVIEW_STATUS_PENDING_REVIEW),
    category: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedEvidenceFindingResponse:
    if review_status not in EVIDENCE_REVIEW_STATUS_VALUES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported review status")
    if category is not None and category not in DISCOVERY_CATEGORY_VALUES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported finding category")

    owned_query = (
        db.query(EvidenceFinding)
        .join(DiscoveryScan, EvidenceFinding.scan_id == DiscoveryScan.id)
        .filter(
            DiscoveryScan.user_id == current_user.id,
            EvidenceFinding.review_status == review_status,
        )
    )
    if category is not None:
        owned_query = owned_query.filter(EvidenceFinding.category == category)

    total_count = owned_query.count()
    findings = (
        owned_query
        .order_by(EvidenceFinding.created_at.asc(), EvidenceFinding.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = (total_count + page_size - 1) // page_size if total_count else 0
    return PaginatedEvidenceFindingResponse(
        items=[_finding_response(finding) for finding in findings],
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/findings/{finding_id}", response_model=EvidenceFindingDetailResponse)
def get_discovery_finding(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvidenceFindingDetailResponse:
    finding = _get_owned_finding(db, finding_id, current_user.id)
    document = (
        db.query(Document)
        .filter(Document.id == finding.document_id, Document.user_id == current_user.id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence finding not found")
    return _finding_detail_response(finding, document)


@router.post(
    "/findings/{finding_id}/assets",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_from_discovery_finding(
    finding_id: str,
    payload: ManualAssetConversionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssetResponse:
    finding = _get_owned_finding(db, finding_id, current_user.id)
    if finding.review_status != EVIDENCE_REVIEW_STATUS_CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only confirmed findings can be used to create an asset",
        )

    existing_link = db.query(DiscoveryFindingAssetLink).filter(DiscoveryFindingAssetLink.finding_id == finding.id).first()
    if existing_link is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An asset has already been created from this finding",
        )

    details = payload.details
    asset_payload = AssetCreate(
        asset_name=payload.asset_name,
        asset_category=payload.asset_category,
        institution=payload.institution,
        description=payload.description,
        estimated_value=payload.estimated_value,
        ownership_type=payload.ownership_type,
        details=details,
    )
    asset = create_asset_record(
        db,
        user_id=current_user.id,
        payload=asset_payload,
        require_manual_verification=True,
        commit=False,
    )
    db.add(DiscoveryFindingAssetLink(
        finding_id=finding.id,
        asset_id=asset.id,
        user_id=current_user.id,
    ))
    try:
        log_event(
            db,
            user_id=current_user.id,
            event_type="asset_created_from_finding",
            details="Asset manually created from confirmed discovery finding",
            metadata={
                "resource_type": "asset",
                "resource_id": asset.id,
                "asset_id": asset.id,
                "finding_id": finding.id,
                "event_type": "asset_created_from_finding",
            },
        )
        db.commit()
        db.refresh(asset)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An asset has already been created from this finding",
        ) from exc
    return _asset_response(asset)


@router.patch("/findings/{finding_id}", response_model=EvidenceFindingResponse)
def review_discovery_finding(
    finding_id: str,
    payload: EvidenceFindingReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvidenceFindingResponse:
    finding = _get_owned_finding(db, finding_id, current_user.id)
    old_status = finding.review_status
    if old_status == payload.review_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Finding is already in the requested review status",
        )

    event_type = _review_event_type(old_status, payload.review_status)
    finding.review_status = payload.review_status
    log_event(
        db,
        user_id=current_user.id,
        event_type=event_type,
        details="Discovery finding review status changed",
        metadata={
            "resource_type": "evidence_finding",
            "resource_id": finding.id,
            "finding_id": finding.id,
            "event_type": event_type,
            "old_status": old_status,
            "new_status": finding.review_status,
        },
    )
    db.commit()
    db.refresh(finding)
    return _finding_response(finding)
