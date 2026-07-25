from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from backend.app.database.connection import Base
import uuid

class DiscoveryScanDocument(Base):
    __tablename__ = "discovery_scan_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("discovery.id"), nullable=False) # Link to a specific discovery scan run
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False) # Link to the actual document
    status = Column(String, nullable=False, default="PENDING") # e.g., PENDING, PROCESSING, COMPLETED, FAILED
    warning_code = Column(String, nullable=True) # e.g., DOCUMENT_TOO_LARGE, EXTRACTION_FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
