from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base

ASSET_STATUS_ACTIVE = "Active"
ASSET_STATUS_ARCHIVED = "Archived"

ASSET_VERIFICATION_UNKNOWN = "UNKNOWN"
ASSET_VERIFICATION_VERIFIED = "VERIFIED"
ASSET_VERIFICATION_NEEDS_REVIEW = "NEEDS_REVIEW"
ASSET_VERIFICATION_CLOSED = "CLOSED"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_category = Column(String, nullable=False, index=True)
    asset_name = Column(String, nullable=False, index=True)
    institution = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    estimated_value = Column(Numeric(12, 2), nullable=True)
    ownership_type = Column(String, nullable=True)
    status = Column(String, nullable=False, default=ASSET_STATUS_ACTIVE)
    is_verified = Column(Boolean, nullable=False, default=False)
    verification_status = Column(String, nullable=False, default=ASSET_VERIFICATION_UNKNOWN)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    modified_by = Column(String, nullable=True)

    user = relationship("User", back_populates="assets")
    details = relationship("AssetDetail", back_populates="asset", cascade="all, delete-orphan", uselist=False)
    beneficiaries = relationship("AssetBeneficiary", back_populates="asset", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="asset", cascade="all, delete-orphan")
