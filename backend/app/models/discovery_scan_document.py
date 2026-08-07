import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.sql import func

from app.database.connection import Base

DISCOVERY_DOCUMENT_STATUS_PENDING = "PENDING"
DISCOVERY_DOCUMENT_STATUS_PROCESSING = "PROCESSING"
DISCOVERY_DOCUMENT_STATUS_COMPLETED = "COMPLETED"
DISCOVERY_DOCUMENT_STATUS_FAILED = "FAILED"
DISCOVERY_DOCUMENT_STATUS_SKIPPED = "SKIPPED"

DISCOVERY_DOCUMENT_STATUS_VALUES = {
    DISCOVERY_DOCUMENT_STATUS_PENDING,
    DISCOVERY_DOCUMENT_STATUS_PROCESSING,
    DISCOVERY_DOCUMENT_STATUS_COMPLETED,
    DISCOVERY_DOCUMENT_STATUS_FAILED,
    DISCOVERY_DOCUMENT_STATUS_SKIPPED,
}

DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED = "PROCESSING_FAILED"
DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION = "UNSUPPORTED_EXTRACTION"
DISCOVERY_DOCUMENT_WARNING_EMPTY_DOCUMENT = "EMPTY_DOCUMENT"


class DiscoveryScanDocument(Base):
    __tablename__ = "discovery_scan_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    scan_id = Column(
        String,
        ForeignKey("discovery_scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id = Column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String, nullable=False, default=DISCOVERY_DOCUMENT_STATUS_PENDING, index=True)
    warning_code = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
