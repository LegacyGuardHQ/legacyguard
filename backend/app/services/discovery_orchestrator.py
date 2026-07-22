from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Callable, Protocol

from sqlalchemy.orm import Session

from app.models.discovery import (
    DISCOVERY_SCAN_STATUS_COMPLETE,
    DISCOVERY_SCAN_STATUS_FAILED,
    DISCOVERY_SCAN_STATUS_PENDING,
    DISCOVERY_SCAN_STATUS_RUNNING,
    EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
    DiscoveryScan,
    EvidenceFinding,
)
from app.models.document import Document
from app.services.discovery_engine import DiscoveryEngine
from app.services.discovery_privacy import DiscoveryPrivacyService
from app.services.document_content_encryption import document_content_encryption_service
from app.services.document_storage import LocalDocumentStorage

DISCOVERY_STARTED = "discovery_started"
DISCOVERY_COMPLETED = "discovery_completed"
DISCOVERY_FAILED = "discovery_failed"
EVIDENCE_FINDING_CREATED = "evidence_finding_created"


class DiscoveryOrchestrationError(RuntimeError):
    pass


class DocumentTextProvider(Protocol):
    def get_text(self, document: Document) -> str:
        ...


class EncryptedDocumentTextProvider:
    def __init__(self, storage: LocalDocumentStorage | None = None) -> None:
        self.storage = storage or LocalDocumentStorage()

    def get_text(self, document: Document) -> str:
        encrypted_key_reference = document.encryption_key_reference_encrypted
        if encrypted_key_reference is None:
            raise DiscoveryOrchestrationError("Document content is unavailable")

        encrypted_bytes = self.storage.read_encrypted(document.id)
        plaintext = document_content_encryption_service.decrypt(document.id, encrypted_bytes, encrypted_key_reference)
        return plaintext.decode("utf-8", errors="replace")


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

    def run_scan(self, db: Session, *, user_id: str, document_ids: list[str]) -> DiscoveryScan:
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
        self._audit(db, user_id, DISCOVERY_STARTED, f"Discovery scan {scan.id} created")

        try:
            documents = self._get_owned_documents(db, user_id=user_id, document_ids=document_ids)
            scan.status = DISCOVERY_SCAN_STATUS_RUNNING
            scan.started_at = datetime.now(timezone.utc)
            db.commit()

            for document in documents:
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
                    self._audit(db, user_id, EVIDENCE_FINDING_CREATED, f"Evidence finding created for scan {scan.id}")
                scan.documents_processed += 1

            scan.status = DISCOVERY_SCAN_STATUS_COMPLETE
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(scan)
            self._audit(db, user_id, DISCOVERY_COMPLETED, f"Discovery scan {scan.id} completed")
            return scan
        except Exception as exc:
            db.rollback()
            scan.status = DISCOVERY_SCAN_STATUS_FAILED
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
            self._audit(db, user_id, DISCOVERY_FAILED, f"Discovery scan {scan.id} failed")
            raise DiscoveryOrchestrationError("Discovery scan failed") from exc

    def _get_owned_documents(self, db: Session, *, user_id: str, document_ids: list[str]) -> list[Document]:
        documents = db.query(Document).filter(Document.id.in_(document_ids), Document.user_id == user_id).all()
        if len(documents) != len(set(document_ids)):
            raise DiscoveryOrchestrationError("One or more documents were not found")
        return documents

    def _audit(self, db: Session, user_id: str, event_type: str, details: str) -> None:
        if self.audit_logger is not None:
            self.audit_logger(db, user_id, event_type, details)