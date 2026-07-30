from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Callable, Protocol

from sqlalchemy.orm import Session

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
    DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED,
    DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION,
    DiscoveryScanDocument,
)
from app.models.document import Document
from app.services.audit import log_event
from app.services.discovery_engine import DiscoveryEngine
from app.services.discovery_privacy import DiscoveryPrivacyService
from app.services.document_content_encryption import document_content_encryption_service
from app.services.document_extraction import EXTRACTION_METHOD_UNSUPPORTED, DocumentExtractionService
from app.services.document_storage import LocalDocumentStorage

DISCOVERY_STARTED = "discovery_started"
DISCOVERY_COMPLETED = "discovery_completed"
DISCOVERY_FAILED = "discovery_failed"
EVIDENCE_FINDING_CREATED = "evidence_finding_created"
DISCOVERY_DOCUMENT_FAILED = "discovery_document_failed"
DISCOVERY_DOCUMENT_COMPLETED = "discovery_document_completed"
DISCOVERY_DOCUMENT_SKIPPED = "discovery_document_skipped"


class DiscoveryOrchestrationError(RuntimeError):
    pass


class UnsupportedDocumentExtractionError(DiscoveryOrchestrationError):
    pass


class DiscoveryScanExecutor:
    def __init__(self, orchestrator: "DiscoveryOrchestrator") -> None:
        self.orchestrator = orchestrator

    def process(self, db: Session, *, user_id: str, document_ids: list[str]) -> DiscoveryScan:
        return self.orchestrator.run_scan(db, user_id=user_id, document_ids=document_ids)

    def create_pending(self, db: Session, *, user_id: str) -> DiscoveryScan:
        return self.orchestrator.create_scan(db, user_id=user_id)

    def process_existing(
        self,
        db: Session,
        *,
        scan_id: str,
        user_id: str,
        document_ids: list[str],
    ) -> DiscoveryScan:
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
        storage: LocalDocumentStorage | None = None,
        extraction_service: DocumentExtractionService | None = None,
    ) -> None:
        self.storage = storage or LocalDocumentStorage()
        self.extraction_service = extraction_service or DocumentExtractionService()

    def get_text(self, document: Document) -> str:
        encrypted_key_reference = document.encryption_key_reference_encrypted
        if encrypted_key_reference is None:
            raise DiscoveryOrchestrationError("Document content is unavailable")

        encrypted_bytes = self.storage.read_encrypted(document.id)
        plaintext = document_content_encryption_service.decrypt(
            document.id,
            encrypted_bytes,
            encrypted_key_reference,
        )
        normalized = self.extraction_service.extract_from_bytes(plaintext, mime_type=document.mime_type)
        if normalized.extraction_method == EXTRACTION_METHOD_UNSUPPORTED:
            raise UnsupportedDocumentExtractionError("Document format extraction is not supported")
        return normalized.text


# Existing tests and integrations provide a simple four-argument callback. The
# built-in audit service is used when no callback is supplied.
AuditLogger = Callable[[Session, str, str, str], None]


class DiscoveryOrchestrator:
    def __init__(
        self,
        *,
        discovery_engine: DiscoveryEngine | None = None,
        privacy_service: DiscoveryPrivacyService | None = None,
        text_provider: DocumentTextProvider | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.discovery_engine = discovery_engine or DiscoveryEngine()
        self.privacy_service = privacy_service or DiscoveryPrivacyService()
        self.text_provider = text_provider or EncryptedDocumentTextProvider()
        self.audit_logger = audit_logger

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
        scan = (
            db.query(DiscoveryScan)
            .filter(
                DiscoveryScan.id == scan_id,
                DiscoveryScan.user_id == user_id,
                DiscoveryScan.status == DISCOVERY_SCAN_STATUS_PENDING,
            )
            .first()
        )
        if scan is None:
            raise DiscoveryOrchestrationError("Pending discovery scan not found")

        try:
            documents = self._get_owned_documents(db, user_id=user_id, document_ids=document_ids)
            old_scan_status = scan.status
            scan.status = DISCOVERY_SCAN_STATUS_RUNNING
            scan.started_at = datetime.now(timezone.utc)
            db.commit()
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
                    "old_status": old_scan_status,
                    "new_status": scan.status,
                },
            )

            document_failures = 0
            documents_skipped = 0
            findings_created = 0
            for document in documents:
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
                    document_text = self.text_provider.get_text(document)
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
                        findings_created += 1
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
                    tracking.warning_code = None
                    scan.documents_processed += 1
                    db.commit()
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
                except UnsupportedDocumentExtractionError:
                    documents_skipped += 1
                    tracking.status = DISCOVERY_DOCUMENT_STATUS_SKIPPED
                    tracking.warning_code = DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION
                    db.commit()
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

            old_scan_status = scan.status
            if document_failures and scan.documents_processed == 0:
                scan.status = DISCOVERY_SCAN_STATUS_FAILED
            elif document_failures and findings_created > 0:
                scan.status = DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS
            elif document_failures:
                scan.status = DISCOVERY_SCAN_STATUS_FAILED
            elif documents_skipped:
                scan.status = DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS
            else:
                scan.status = DISCOVERY_SCAN_STATUS_COMPLETE
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(scan)

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
            return scan
        except Exception as exc:
            db.rollback()
            scan = db.query(DiscoveryScan).filter(DiscoveryScan.id == scan.id).one()
            old_scan_status = scan.status
            scan.status = DISCOVERY_SCAN_STATUS_FAILED
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
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
            raise DiscoveryOrchestrationError("Discovery scan failed") from exc

    def mark_scan_failed(self, db: Session, *, scan_id: str, user_id: str) -> DiscoveryScan | None:
        db.rollback()
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
        db.commit()
        db.refresh(scan)
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
