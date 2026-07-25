from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.models.discovery import EVIDENCE_REVIEW_STATUS_PENDING_REVIEW, EVIDENCE_REVIEW_STATUS_VALUES, DiscoveryScan, EvidenceFinding
from app.models.user import User
from app.schemas.discovery import (
    DiscoveryReportSummaryResponse,
    DiscoverySafeReportResponse,
    DiscoveryScanCreate,
    DiscoveryScanResponse,
    DiscoveryScanStatusResponse,
    DiscoveryScanSummaryResponse,
    EvidenceFindingResponse,
    EvidenceFindingReviewRequest,
    PaginatedDiscoveryScanResponse,
    PaginatedEvidenceFindingResponse,
)
from app.security.auth import get_current_user, get_db
from app.services.audit import log_event
from app.services.discovery_orchestrator import DiscoveryOrchestrationError, DiscoveryOrchestrator
from app.services.discovery_reports import DiscoveryReportService

router = APIRouter(prefix="/discovery", tags=["discovery"])
discovery_orchestrator = DiscoveryOrchestrator()
discovery_report_service = DiscoveryReportService()


def _scan_response(scan: DiscoveryScan) -> DiscoveryScanResponse:
    return DiscoveryScanResponse(scan_id=scan.id, status=scan.status, created_at=scan.created_at)


def _scan_status_response(scan: DiscoveryScan) -> DiscoveryScanStatusResponse:
    return DiscoveryScanStatusResponse(
        scan_id=scan.id,
        status=scan.status,
        documents_processed=scan.documents_processed,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
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
    return _scan_status_response(scan)


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


@router.get("/findings/review-queue", response_model=PaginatedEvidenceFindingResponse)
def list_discovery_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    review_status: str = Query(EVIDENCE_REVIEW_STATUS_PENDING_REVIEW),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedEvidenceFindingResponse:
    if review_status not in EVIDENCE_REVIEW_STATUS_VALUES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported review status")

    owned_query = (
        db.query(EvidenceFinding)
        .join(DiscoveryScan, EvidenceFinding.scan_id == DiscoveryScan.id)
        .filter(
            DiscoveryScan.user_id == current_user.id,
            EvidenceFinding.review_status == review_status,
        )
    )
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
    db.commit()
    db.refresh(finding)
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
    return _finding_response(finding)