import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import SessionLocal
from app.models.asset import ASSET_STATUS_ARCHIVED, Asset
from app.models.beneficiary import BENEFICIARY_STATUS_ARCHIVED, Beneficiary
from app.models.document import DOCUMENT_STATUS_ACTIVE, DOCUMENT_VERIFICATION_UNKNOWN, Document
from app.models.user import User
from app.schemas.documents import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadDiscoveryScanResponse,
    DocumentUploadResponse,
)
from app.security.auth import get_current_user, get_db
from app.services.discovery_orchestrator import (
    DiscoveryOrchestrator,
    DiscoveryScanAlreadyClaimedError,
    DiscoveryScanExecutor,
)
from app.services.document_content_encryption import DocumentContentEncryptionError, document_content_encryption_service
from app.services.document_storage import DocumentStorageError, LocalDocumentStorage
from app.services.document_storage_config import get_default_document_storage_root
from app.services.document_validation import (
    MAX_DOCUMENT_BYTES,
    DocumentValidationError,
    MalwareScanner,
    calculate_checksum_sha256,
    validate_document_size,
    validate_extension_and_mime,
    validate_magic_bytes,
)

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)
malware_scanner: MalwareScanner | None = None
UPLOAD_READ_CHUNK_BYTES = 64 * 1024


def _build_document_storage() -> LocalDocumentStorage:
    return LocalDocumentStorage(get_default_document_storage_root())


document_storage = _build_document_storage()


async def _read_bounded_upload(file: UploadFile) -> bytes:
    content = bytearray()
    while True:
        chunk = await file.read(UPLOAD_READ_CHUNK_BYTES)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_DOCUMENT_BYTES:
            raise DocumentValidationError("Document exceeds maximum size")
    validate_document_size(len(content))
    return bytes(content)

def _build_discovery_orchestrator() -> DiscoveryOrchestrator:
    return DiscoveryOrchestrator(stale_scan_threshold_seconds=settings.discovery_stale_scan_threshold_seconds)


default_discovery_scan_executor = DiscoveryScanExecutor(_build_discovery_orchestrator())
discovery_scan_executor = default_discovery_scan_executor


def _get_owned_asset_if_supplied(db: Session, asset_id: str | None, user_id: str) -> Asset | None:
    if asset_id is None:
        return None
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == user_id).first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    if asset.archived_at is not None or asset.status == ASSET_STATUS_ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archived assets cannot be linked to documents")
    return asset


def _get_owned_beneficiary_if_supplied(db: Session, beneficiary_id: str | None, user_id: str) -> Beneficiary | None:
    if beneficiary_id is None:
        return None
    beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary_id, Beneficiary.user_id == user_id).first()
    if beneficiary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found")
    if beneficiary.archived_at is not None or beneficiary.status == BENEFICIARY_STATUS_ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archived beneficiaries cannot be linked to documents")
    return beneficiary


def _document_list_response(document: Document) -> DocumentListResponse:
    return DocumentListResponse(
        id=document.id,
        asset_id=document.asset_id,
        beneficiary_id=document.beneficiary_id,
        document_type=document.document_type,
        document_name=document.document_name,
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        file_size=document.file_size,
        status=document.status,
        verification_status=document.verification_status,
        verified_at=document.verified_at,
        review_due_at=document.review_due_at,
        effective_date=document.effective_date,
        expiration_date=document.expiration_date,
        archived_at=document.archived_at,
        version_number=document.version_number,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _document_response(document: Document) -> DocumentResponse:
    return DocumentResponse(**_document_list_response(document).model_dump(), description=document.get_description())


def _get_owned_document(db: Session, document_id: str, user_id: str) -> Document:
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _trigger_discovery_scan_after_upload(
    db: Session,
    background_tasks: BackgroundTasks,
    *,
    user_id: str,
    document_id: str,
) -> DocumentUploadDiscoveryScanResponse | None:
    scan = discovery_scan_executor.create_pending(db, user_id=user_id)
    try:
        background_tasks.add_task(
            _process_discovery_scan_in_background,
            scan.id,
            user_id,
            document_id,
        )
    except Exception:
        db.rollback()
        try:
            discovery_scan_executor.mark_failed(db, scan_id=scan.id, user_id=user_id)
        except Exception:
            db.rollback()
            logger.exception(
                "Failed to mark unscheduled discovery scan as failed",
                extra={"scan_id": scan.id, "user_id": user_id},
            )
        raise
    return DocumentUploadDiscoveryScanResponse(scan_id=scan.id, status=scan.status)


def _process_discovery_scan_in_background(scan_id: str, user_id: str, document_id: str) -> None:
    db: Session | None = None
    try:
        db = SessionLocal()
        discovery_scan_executor.process_existing(
            db,
            scan_id=scan_id,
            user_id=user_id,
            document_ids=[document_id],
        )
    except DiscoveryScanAlreadyClaimedError:
        if db is not None:
            db.rollback()
        logger.info(
            "Background discovery scan was already claimed or completed",
            extra={"scan_id": scan_id, "user_id": user_id},
        )
    except Exception:
        if db is not None:
            db.rollback()
        logger.exception(
            "Background discovery processing failed",
            extra={"scan_id": scan_id, "user_id": user_id},
        )
        if db is not None:
            try:
                discovery_scan_executor.mark_failed(db, scan_id=scan_id, user_id=user_id)
            except Exception:
                db.rollback()
                logger.exception(
                    "Failed to record background discovery failure",
                    extra={"scan_id": scan_id, "user_id": user_id},
                )
    finally:
        if db is not None:
            db.close()


def _validate_document_upload_lifecycle(db: Session, document: Document, user_id: str) -> None:
    if document.archived_at is not None or document.status != DOCUMENT_STATUS_ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archived documents cannot receive uploads")
    _get_owned_asset_if_supplied(db, document.asset_id, user_id)
    _get_owned_beneficiary_if_supplied(db, document.beneficiary_id, user_id)
    if document.storage_reference_encrypted is not None or document.encryption_key_reference_encrypted is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document already has uploaded content")


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document_metadata(
    payload: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    _get_owned_asset_if_supplied(db, payload.asset_id, current_user.id)
    _get_owned_beneficiary_if_supplied(db, payload.beneficiary_id, current_user.id)

    now = datetime.now(timezone.utc)
    document = Document(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        asset_id=payload.asset_id,
        beneficiary_id=payload.beneficiary_id,
        document_type=payload.document_type,
        document_name=payload.document_name,
        original_filename=payload.original_filename,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
        status=DOCUMENT_STATUS_ACTIVE,
        verification_status=DOCUMENT_VERIFICATION_UNKNOWN,
        verified_at=None,
        review_due_at=payload.review_due_at,
        effective_date=payload.effective_date,
        expiration_date=payload.expiration_date,
        archived_at=None,
        version_number=payload.version_number,
        created_at=now,
        updated_at=now,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    document.set_description(payload.description)
    document.storage_reference = None
    document.storage_reference_encrypted = None
    document.encryption_key_reference_encrypted = None
    document.checksum_sha256 = None
    db.add(document)
    db.commit()
    db.refresh(document)
    return _document_response(document)


@router.get("", response_model=list[DocumentListResponse])
def list_document_metadata(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DocumentListResponse]:
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id, Document.archived_at.is_(None))
        .order_by(Document.created_at.asc())
        .all()
    )
    return [_document_list_response(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_metadata(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    document = _get_owned_document(db, document_id, current_user.id)
    return _document_response(document)


@router.post("/{document_id}/upload", response_model=DocumentUploadResponse)
async def upload_encrypted_document_content(
    document_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    document = _get_owned_document(db, document_id, current_user.id)
    _validate_document_upload_lifecycle(db, document, current_user.id)

    try:
        content = await _read_bounded_upload(file)
        filename, _extension = validate_extension_and_mime(file.filename or "", file.content_type or "")
        validate_magic_bytes(content, file.content_type or "")
        if malware_scanner is not None:
            malware_scanner.scan(content)
        encrypted = document_content_encryption_service.encrypt(document.id, content)
    except (DocumentValidationError, DocumentContentEncryptionError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected document upload preparation failure", extra={"document_id": document.id})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Document upload failed") from exc

    storage_reference: str | None = None
    try:
        storage_reference = document_storage.save_encrypted(document.id, encrypted.encrypted_bytes)
        now = datetime.now(timezone.utc)
        document.original_filename = filename
        document.mime_type = file.content_type
        document.file_size = len(content)
        document.checksum_sha256 = calculate_checksum_sha256(content)
        document.set_storage_reference(storage_reference)
        document.encryption_key_reference_encrypted = encrypted.encrypted_key_reference
        document.content_encryption_version = encrypted.content_encryption_version
        document.modified_by = current_user.id
        document.updated_at = now
        db.commit()
        db.refresh(document)
    except DocumentStorageError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Document storage failed") from exc
    except Exception as exc:
        db.rollback()
        if storage_reference is not None:
            try:
                document_storage.delete_permanently(document.id)
            except Exception:
                logger.exception("Failed to remove orphaned encrypted document content", extra={"document_id": document.id})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Document upload failed") from exc

    try:
        discovery_scan = _trigger_discovery_scan_after_upload(
            db,
            background_tasks,
            user_id=current_user.id,
            document_id=document.id,
        )
    except Exception:
        db.rollback()
        logger.exception(
            "Post-upload discovery processing failed",
            extra={"document_id": document.id, "user_id": current_user.id},
        )
        discovery_scan = None

    return DocumentUploadResponse(
        id=document.id,
        document_type=document.document_type,
        document_name=document.document_name,
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        file_size=document.file_size,
        checksum_sha256=document.checksum_sha256,
        upload_status="COMPLETED",
        updated_at=document.updated_at,
        discovery_scan=discovery_scan,
    )
