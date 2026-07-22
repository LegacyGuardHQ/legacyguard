from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database.connection import Base
from app.services.encryption import encryption_service

DISCOVERY_SCAN_STATUS_PENDING = "PENDING"
DISCOVERY_SCAN_STATUS_RUNNING = "RUNNING"
DISCOVERY_SCAN_STATUS_COMPLETE = "COMPLETE"
DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
DISCOVERY_SCAN_STATUS_FAILED = "FAILED"

DISCOVERY_SCAN_STATUS_VALUES = {
    DISCOVERY_SCAN_STATUS_PENDING,
    DISCOVERY_SCAN_STATUS_RUNNING,
    DISCOVERY_SCAN_STATUS_COMPLETE,
    DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS,
    DISCOVERY_SCAN_STATUS_FAILED,
}

EVIDENCE_REVIEW_STATUS_PENDING_REVIEW = "PENDING_REVIEW"
EVIDENCE_REVIEW_STATUS_CONFIRMED = "CONFIRMED"
EVIDENCE_REVIEW_STATUS_DISMISSED = "DISMISSED"

EVIDENCE_REVIEW_STATUS_VALUES = {
    EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
    EVIDENCE_REVIEW_STATUS_CONFIRMED,
    EVIDENCE_REVIEW_STATUS_DISMISSED,
}


class DiscoveryScan(Base):
    __tablename__ = "discovery_scans"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, default=DISCOVERY_SCAN_STATUS_PENDING, index=True)
    documents_processed = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EvidenceFinding(Base):
    __tablename__ = "evidence_findings"

    id = Column(String, primary_key=True, index=True)
    scan_id = Column(String, ForeignKey("discovery_scans.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    confidence_score = Column(Float, nullable=False)
    matched_terms_encrypted = Column(Text, nullable=True)
    evidence_excerpt_encrypted = Column(Text, nullable=True)
    review_status = Column(String, nullable=False, default=EVIDENCE_REVIEW_STATUS_PENDING_REVIEW, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def set_matched_terms(self, matched_terms: str | None) -> None:
        if matched_terms is not None:
            self.matched_terms_encrypted = encryption_service.encrypt(matched_terms)

    def get_matched_terms(self) -> str | None:
        if self.matched_terms_encrypted is None:
            return None
        return encryption_service.decrypt(self.matched_terms_encrypted)

    def set_evidence_excerpt(self, evidence_excerpt: str | None) -> None:
        if evidence_excerpt is not None:
            self.evidence_excerpt_encrypted = encryption_service.encrypt(evidence_excerpt)

    def get_evidence_excerpt(self) -> str | None:
        if self.evidence_excerpt_encrypted is None:
            return None
        return encryption_service.decrypt(self.evidence_excerpt_encrypted)
