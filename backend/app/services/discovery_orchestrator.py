from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from threading import BoundedSemaphore
from typing import Callable, Protocol

from sqlalchemy.orm import Session

from app.config import settings
from app.models.discovery import (
    DISCOVERY_SCAN_STATUS_COMPLETE,
    DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS,
    DISCOVERY_SCAN_STATUS_FAILED,
    DISCOVERY_SCAN_STATUS_PENDING,
    DISCOVERY_SCAN_STATUS_RUNNING,
    EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
    DiscoveryScan,
    EvidenceFinding,
)
from app.models.discovery_scan_document import (
    DISCOVERY_DOCUMENT_STATUS_COMPLETED,
    DISCOVERY_DOCUMENT_STATUS_FAILED,
    DISCOVERY_DOCUMENT_STATUS_PROCESSING,
    DISCOVERY_DOCUMENT_STATUS_SKIPPED,
    DISCOVERY_DOCUMENT_WARNING_EMPTY_DOCUMENT,
    DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED,
    DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION,
    DiscoveryScanDocument,
)
from app.models.document import DOCUMENT_STORAGE_STORED, Document
from app.models.user import User
from app.services.audit import log_event
from app.services.discovery_engine import DiscoveryEngine
from app.services.discovery_privacy import DiscoveryPrivacyService
from app.services.document_content_encryption import document_content_encryption_service
from app.services.document_extraction import (
    EXTRACTION_METHOD_UNSUPPORTED,
    DocumentExtractionService,
    ExtractedDocumentText,
)
from app.services.document_storage import DocumentStorage
from app.services.document_storage_factory import build_document_storage

DISCOVERY_STARTED = "discovery_started"
DISCOVERY_COMPLETED = "discovery_completed"
DISCOVERY_FAILED = "discovery_failed"
EVIDENCE_FINDING_CREATED = "evidence_finding_created"
DISCOVERY_DOCUMENT_FAILED = "discovery_document_failed"
DISCOVERY_DOCUMENT_COMPLETED = "discovery_document_completed"
DISCOVERY_DOCUMENT_SKIPPED = "discovery_document_skipped"
DISCOVERY_SCAN_CONCURRENCY_LIMIT = 2
_discovery_scan_slots = BoundedSemaphore(DISCOVERY_SCAN_CONCURRENCY_LIMIT)
DISCOVERY_SCAN_QUEUE_LIMIT = 2
_discovery_scan_queue_slots = BoundedSemaphore(DISCOVERY_SCAN_QUEUE_LIMIT)


class DiscoveryOrchestrationError(RuntimeError):
    pass


class DiscoveryScanAlreadyClaimedError(DiscoveryOrchestrationError):
    pass


class DiscoveryScanCapacityError(DiscoveryOrchestrationError):
    pass


class DiscoveryUserScanLimitError(DiscoveryOrchestrationError):
    pass


class UnsupportedDocumentExtractionError(DiscoveryOrchestrationError):
    pass


class DiscoveryScanExecutor:
    def __init__(self, orchestrator: "DiscoveryOrchestrator") -> None:
        self.orchestrator = orchestrator

    def process(self, db: Session, *, user_id: str, document_ids: list[str]) -> DiscoveryScan:
        with _discovery_scan_slots:
            return self.orchestrator.run_scan(db, user_id=user_id, document_ids=document_ids)

    def create_pending(self, db: Session, *, user_id: str) -> DiscoveryScan:
        return self.orchestrator.create_scan(db, user_id=user_id)

    def create_pending_bounded(self, db: Session, *, user_id: str) -> DiscoveryScan:
        # PostgreSQL row locking makes the active-count check and pending insert
        # serial for each user. SQLite serializes the subsequent write itself.
        if not _discovery_scan_queue_slots.acquire(blocking=False):
            raise DiscoveryScanCapacityError("Discovery processing capacity is currently full")
        try:
            db.query(User.id).filter(User.id == user_id).with_for_update().one()
            self._expire_stale_pending_scans(db, user_id=user_id)
            active_scan_count = (
                db.query(DiscoveryScan)
                .filter(
                    DiscoveryScan.user_id == user_id,
                    DiscoveryScan.status.in_({DISCOVERY_SCAN_STATUS_PENDING, DISCOVERY_SCAN_STATUS_RUNNING}),
                )
                .count()
            )
            if active_scan_count >= 1:
                raise DiscoveryUserScanLimitError("A discovery scan is already active for this account")
            return self.create_pending(db, user_id=user_id)
        except Exception:
            _discovery_scan_queue_slots.release()
            raise

    def _expire_stale_pending_scans(self, db: Session, *, user_id: str) -> None:
        threshold_seconds = self.orchestrator.stale_scan_threshold_seconds
        if threshold_seconds is None:
            return
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=threshold_seconds)
        (
            db.query(DiscoveryScan)
            .filter(
                DiscoveryScan.user_id == user_id,
                DiscoveryScan.status == DISCOVERY_SCAN_STATUS_PENDING,
                DiscoveryScan.created_at <= cutoff,
            )
            .update(
                {
                    DiscoveryScan.status: DISCOVERY_SCAN_STATUS_FAILED,
                    DiscoveryScan.completed_at: now,
                },
                synchronize_session=False,
            )
        )

    @staticmethod
    def release_pending_slot() -> None:
        _discovery_scan_queue_slots.release()

    def process_existing(
        self,
        db: Session,
        *,
        scan_id: str,
        user_id: str,
        document_ids: list[str],
    ) -> DiscoveryScan:
        with _discovery_scan_slots:
            return self.orchestrator.process_scan(
                db,
                scan_id=scan_id,
                user_id=user_id,
                document_ids=document_ids,
            )

    def mark_failed(self, db: Session, *, scan_id: str, user_id: str) -> DiscoveryScan | None:
        return self.orchestrator.mark_scan_failed(db, scan_id=scan_id, user_id=user_id)


class DocumentTextProvider(Protocol):
    def get_text(self, document: Document) -> str:
        ...


class EncryptedDocumentTextProvider:
    def __init__(
        self,
        storage: DocumentStorage | None = None,
        extraction_service: DocumentExtractionService | None = None,
    ) -> None:
        self.storage = storage or build_document_storage()
        self.extraction_service = extraction_service or DocumentExtractionService()

    def get_text(self, document: Document) -> str:
        if document.storage_state != DOCUMENT_STORAGE_STORED:
            raise DiscoveryOrchestrationError("Document content is not in an eligible storage state")
        encrypted_key_reference = document.encryption_key_reference_encrypted
        if encrypted_key_reference is None:
            raise DiscoveryOrchestrationError("Document content is unavailable")

        try:
            storage_locator = document.get_storage_reference()
        except Exception as exc:
            raise DiscoveryOrchestrationError("Document storage locator is unavailable") from exc
        if storage_locator is None:
            raise DiscoveryOrchestrationError("Document storage locator is unavailable")

        encrypted_bytes = self.storage.read_encrypted(
            storage_locator,
            expected_sha256=document.ciphertext_sha256,
            expected_size=document.ciphertext_size,
        )
        plaintext = document_content_encryption_service.decrypt(
            document.id,
            encrypted_bytes,
            encrypted_key_reference,
        )
        normalized = self.extraction_service.extract_from_bytes(plaintext, mime_type=document.mime_type)
        if normalized.extraction_method == EXTRACTION_METHOD_UNSUPPORTED:
            raise UnsupportedDocumentExtractionError("Document format extraction is not supported")
        return ExtractedDocumentText(normalized.text, warnings=normalized.warnings)


# Existing tests and integrations provide a simple four-argument callback. Audit
# callbacks may add or flush rows but must not commit, roll back, or close the
# caller-owned session. The built-in audit service is used when none is supplied.
AuditLogger = Callable[[Session, str, str, str], None]


class DiscoveryOrchestrator:
    def __init__(
        self,
        *,
        discovery_engine: DiscoveryEngine | None = None,
        privacy_service: DiscoveryPrivacyService | None = None,
        text_provider: DocumentTextProvider | None = None,
        audit_logger: AuditLogger | None = None,
        stale_scan_threshold_seconds: int | None = None,
    ) -> None:
        self.discovery_engine = discovery_engine or DiscoveryEngine()
        self.privacy_service = privacy_service or DiscoveryPrivacyService()
        self.text_provider = text_provider or EncryptedDocumentTextProvider()
        self.audit_logger = audit_logger
        self.stale_scan_threshold_seconds = stale_scan_threshold_seconds

    def create_scan(self, db: Session, *, user_id: str) -> DiscoveryScan:
        scan = DiscoveryScan(
            id=str(uuid.uuid4()),
            user_id=user_id,
            status=DISCOVERY_SCAN_STATUS_PENDING,
            documents_processed=0,
            started_at=None,
            completed_at=None,
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        try:
            self._audit(
                db,
                user_id,
                DISCOVERY_STARTED,
                "Discovery scan created",
                metadata={
                    "resource_type": "discovery_scan",
                    "resource_id": scan.id,
                    "scan_id": scan.id,
                    "event_type": DISCOVERY_STARTED,
                    "new_status": DISCOVERY_SCAN_STATUS_PENDING,
                },
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            try:
                self.mark_scan_failed(db, scan_id=scan.id, user_id=user_id)
            except Exception:
                db.rollback()
            raise DiscoveryOrchestrationError("Discovery scan creation failed") from exc
        return scan

    def run_scan(self, db: Session, *, user_id: str, document_ids: list[str]) -> DiscoveryScan:
        scan = self.create_scan(db, user_id=user_id)
        return self.process_scan(
            db,
            scan_id=scan.id,
            user_id=user_id,
            document_ids=document_ids,
        )

    def process_scan(
        self,
        db: Session,
        *,
        scan_id: str,
        user_id: str,
        document_ids: list[str],
    ) -> DiscoveryScan:
        started_at = datetime.now(timezone.utc)
        existing_scan = db.query(DiscoveryScan).filter(DiscoveryScan.id == scan_id).first()
        if existing_scan is None or existing_scan.user_id != user_id:
            raise DiscoveryOrchestrationError("Discovery scan not found")

        if existing_scan.status == DISCOVERY_SCAN_STATUS_PENDING:
            claimed_rows = (
                db.query(DiscoveryScan)
                .filter(
                    DiscoveryScan.id == scan_id,
                    DiscoveryScan.user_id == user_id,
                    DiscoveryScan.status == DISCOVERY_SCAN_STATUS_PENDING,
                )
                .update(
                    {
                        DiscoveryScan.status: DISCOVERY_SCAN_STATUS_RUNNING,
                        DiscoveryScan.started_at: started_at,
                    },
                    synchronize_session=False,
                )
            )
            if claimed_rows != 1:
                db.rollback()
                raise DiscoveryScanAlreadyClaimedError("Discovery scan is not pending")
            db.commit()
            scan = db.query(DiscoveryScan).filter(DiscoveryScan.id == scan_id, DiscoveryScan.user_id == user_id).one()
        elif self._is_stale_running_scan(existing_scan):
            self._reset_stale_running_scan(db, scan=existing_scan, user_id=user_id, started_at=started_at)
            scan = db.query(DiscoveryScan).filter(DiscoveryScan.id == scan_id, DiscoveryScan.user_id == user_id).one()
        else:
            raise DiscoveryScanAlreadyClaimedError("Discovery scan is not pending")

        try:
            documents = self._get_owned_documents(db, user_id=user_id, document_ids=document_ids)
            self._audit(
                db,
                user_id,
                DISCOVERY_STARTED,
                "Discovery scan started",
                metadata={
                    "resource_type": "discovery_scan",
                    "resource_id": scan.id,
                    "scan_id": scan.id,
                    "event_type": DISCOVERY_STARTED,
                    "old_status": DISCOVERY_SCAN_STATUS_PENDING,
                    "new_status": scan.status,
                },
            )
            db.commit()

            document_failures = 0
            documents_skipped = 0
            documents_with_warnings = 0
            findings_created = 0
            for document in documents:
                document_findings_created = 0
                tracking = DiscoveryScanDocument(
                    id=str(uuid.uuid4()),
                    scan_id=scan.id,
                    document_id=document.id,
                    status=DISCOVERY_DOCUMENT_STATUS_PROCESSING,
                )
                db.add(tracking)
                db.commit()
                db.refresh(tracking)

                try:
                    extracted_result = self.text_provider.get_text(document)
                    document_text = str(extracted_result)
                    document_warnings = list(getattr(extracted_result, "warnings", []) or [])
                    candidates = self.discovery_engine.analyze_text(document_text)
                    for candidate in candidates:
                        privacy_result = self.privacy_service.sanitize_evidence(
                            matched_terms=candidate.matched_terms,
                            evidence_excerpt=None,
                        )
                        finding = EvidenceFinding(
                            id=str(uuid.uuid4()),
                            scan_id=scan.id,
                            document_id=document.id,
                            category=candidate.category,
                            confidence_score=candidate.confidence_score,
                            review_status=EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
                        )
                        finding.set_matched_terms(json.dumps(privacy_result.sanitized_terms))
                        finding.set_evidence_excerpt(privacy_result.sanitized_excerpt)
                        db.add(finding)
                        document_findings_created += 1
                        self._audit(
                            db,
                            user_id,
                            EVIDENCE_FINDING_CREATED,
                            "Evidence finding created",
                            metadata={
                                "resource_type": "evidence_finding",
                                "resource_id": finding.id,
                                "finding_id": finding.id,
                                "scan_id": scan.id,
                                "event_type": EVIDENCE_FINDING_CREATED,
                            },
                        )

                    tracking.status = DISCOVERY_DOCUMENT_STATUS_COMPLETED
                    tracking.warning_code = (
                        DISCOVERY_DOCUMENT_WARNING_EMPTY_DOCUMENT
                        if any(warning == "Document content is empty" for warning in document_warnings)
                        else None
                    )
                    if document_warnings:
                        documents_with_warnings += 1
                    scan.documents_processed += 1
                    self._audit(
                        db,
                        user_id,
                        DISCOVERY_DOCUMENT_COMPLETED,
                        "Discovery document processing completed",
                        metadata={
                            "resource_type": "discovery_scan_document",
                            "resource_id": tracking.id,
                            "scan_id": scan.id,
                            "document_id": document.id,
                            "discovery_scan_document_id": tracking.id,
                            "event_type": DISCOVERY_DOCUMENT_COMPLETED,
                            "old_status": DISCOVERY_DOCUMENT_STATUS_PROCESSING,
                            "new_status": DISCOVERY_DOCUMENT_STATUS_COMPLETED,
                        },
                    )
                    db.commit()
                    findings_created += document_findings_created
                except UnsupportedDocumentExtractionError:
                    documents_skipped += 1
                    tracking.status = DISCOVERY_DOCUMENT_STATUS_SKIPPED
                    tracking.warning_code = DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION
                    self._audit(
                        db,
                        user_id,
                        DISCOVERY_DOCUMENT_SKIPPED,
                        "Discovery document skipped because extraction is unsupported",
                        metadata={
                            "resource_type": "discovery_scan_document",
                            "resource_id": tracking.id,
                            "scan_id": scan.id,
                            "document_id": document.id,
                            "discovery_scan_document_id": tracking.id,
                            "event_type": DISCOVERY_DOCUMENT_SKIPPED,
                            "old_status": DISCOVERY_DOCUMENT_STATUS_PROCESSING,
                            "new_status": DISCOVERY_DOCUMENT_STATUS_SKIPPED,
                            "warning_code": DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION,
                        },
                    )
                    db.commit()
                except Exception:
                    db.rollback()
                    document_failures += 1
                    tracking = db.query(DiscoveryScanDocument).filter(DiscoveryScanDocument.id == tracking.id).one()
                    tracking.status = DISCOVERY_DOCUMENT_STATUS_FAILED
                    tracking.warning_code = DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED
                    db.commit()
                    self._audit(
                        db,
                        user_id,
                        DISCOVERY_DOCUMENT_FAILED,
                        "Discovery document processing failed",
                        metadata={
                            "resource_type": "discovery_scan_document",
                            "resource_id": tracking.id,
                            "scan_id": scan.id,
                            "document_id": document.id,
                            "discovery_scan_document_id": tracking.id,
                            "event_type": DISCOVERY_DOCUMENT_FAILED,
                            "old_status": DISCOVERY_DOCUMENT_STATUS_PROCESSING,
                            "new_status": DISCOVERY_DOCUMENT_STATUS_FAILED,
                        },
                    )
                    db.commit()

            old_scan_status = scan.status
            if document_failures and scan.documents_processed == 0:
                scan.status = DISCOVERY_SCAN_STATUS_FAILED
            elif document_failures and findings_created > 0:
                scan.status = DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS
            elif document_failures:
                scan.status = DISCOVERY_SCAN_STATUS_FAILED
            elif documents_with_warnings or documents_skipped:
                scan.status = DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS
            else:
                scan.status = DISCOVERY_SCAN_STATUS_COMPLETE
            scan.completed_at = datetime.now(timezone.utc)

            if scan.status == DISCOVERY_SCAN_STATUS_FAILED:
                self._audit(
                    db,
                    user_id,
                    DISCOVERY_FAILED,
                    "Discovery scan failed",
                    metadata={
                        "resource_type": "discovery_scan",
                        "resource_id": scan.id,
                        "scan_id": scan.id,
                        "event_type": DISCOVERY_FAILED,
                        "old_status": old_scan_status,
                        "new_status": scan.status,
                    },
                )
                db.commit()
                db.refresh(scan)
                raise DiscoveryOrchestrationError("Discovery scan failed")

            self._audit(
                db,
                user_id,
                DISCOVERY_COMPLETED,
                "Discovery scan completed",
                metadata={
                    "resource_type": "discovery_scan",
                    "resource_id": scan.id,
                    "scan_id": scan.id,
                    "event_type": DISCOVERY_COMPLETED,
                    "old_status": old_scan_status,
                    "new_status": scan.status,
                },
            )
            db.commit()
            db.refresh(scan)
            return scan
        except Exception as exc:
            db.rollback()
            try:
                self.mark_scan_failed(db, scan_id=scan_id, user_id=user_id)
            except Exception:
                db.rollback()
            raise DiscoveryOrchestrationError("Discovery scan failed") from exc

    def _is_stale_running_scan(self, scan: DiscoveryScan) -> bool:
        if scan.status != DISCOVERY_SCAN_STATUS_RUNNING:
            return False
        if self.stale_scan_threshold_seconds is None:
            return False
        if scan.started_at is None:
            return False
        threshold = timedelta(seconds=self.stale_scan_threshold_seconds)
        now = datetime.now(timezone.utc)
        if scan.started_at.tzinfo is None:
            scan_started_at = scan.started_at.replace(tzinfo=timezone.utc)
        else:
            scan_started_at = scan.started_at
        return now - scan_started_at >= threshold

    def _reset_stale_running_scan(self, db: Session, *, scan: DiscoveryScan, user_id: str, started_at: datetime) -> None:
        scan.status = DISCOVERY_SCAN_STATUS_PENDING
        scan.started_at = None
        scan.completed_at = None
        scan.documents_processed = 0
        db.query(DiscoveryScanDocument).filter(DiscoveryScanDocument.scan_id == scan.id).delete(synchronize_session=False)
        db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == scan.id).delete(synchronize_session=False)
        db.commit()
        self._audit(
            db,
            user_id,
            DISCOVERY_STARTED,
            "Discovery scan recovered from stale running state",
            metadata={
                "resource_type": "discovery_scan",
                "resource_id": scan.id,
                "scan_id": scan.id,
                "event_type": DISCOVERY_STARTED,
                "old_status": DISCOVERY_SCAN_STATUS_RUNNING,
                "new_status": DISCOVERY_SCAN_STATUS_PENDING,
            },
        )
        db.commit()

        claimed_rows = (
            db.query(DiscoveryScan)
            .filter(
                DiscoveryScan.id == scan.id,
                DiscoveryScan.user_id == user_id,
                DiscoveryScan.status == DISCOVERY_SCAN_STATUS_PENDING,
            )
            .update(
                {
                    DiscoveryScan.status: DISCOVERY_SCAN_STATUS_RUNNING,
                    DiscoveryScan.started_at: started_at,
                },
                synchronize_session=False,
            )
        )
        if claimed_rows != 1:
            db.rollback()
            raise DiscoveryScanAlreadyClaimedError("Discovery scan is not pending")
        db.commit()

    def mark_scan_failed(self, db: Session, *, scan_id: str, user_id: str) -> DiscoveryScan | None:
        """Persist failure using a usable caller-owned session.

        Callers recovering from a failed transaction must roll back before
        invoking this method.
        """
        scan = (
            db.query(DiscoveryScan)
            .filter(DiscoveryScan.id == scan_id, DiscoveryScan.user_id == user_id)
            .first()
        )
        if scan is None:
            return None
        if scan.status not in {DISCOVERY_SCAN_STATUS_PENDING, DISCOVERY_SCAN_STATUS_RUNNING}:
            return scan

        old_scan_status = scan.status
        scan.status = DISCOVERY_SCAN_STATUS_FAILED
        scan.completed_at = datetime.now(timezone.utc)
        try:
            self._audit(
                db,
                user_id,
                DISCOVERY_FAILED,
                "Discovery scan failed",
                metadata={
                    "resource_type": "discovery_scan",
                    "resource_id": scan.id,
                    "scan_id": scan.id,
                    "event_type": DISCOVERY_FAILED,
                    "old_status": old_scan_status,
                    "new_status": scan.status,
                },
            )
            db.commit()
            db.refresh(scan)
        except Exception:
            db.rollback()
            raise
        return scan

    def _get_owned_documents(self, db: Session, *, user_id: str, document_ids: list[str]) -> list[Document]:
        documents = db.query(Document).filter(Document.id.in_(document_ids), Document.user_id == user_id).all()
        if len(documents) != len(set(document_ids)):
            raise DiscoveryOrchestrationError("One or more documents were not found")
        return documents

    def _audit(
        self,
        db: Session,
        user_id: str,
        event_type: str,
        details: str,
        *,
        metadata: dict[str, object] | None = None,
    ) -> None:
        if self.audit_logger is not None:
            self.audit_logger(db, user_id, event_type, details)
            return
        log_event(
            db,
            user_id=user_id,
            event_type=event_type,
            details=details,
            metadata=metadata,
        )
