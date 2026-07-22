import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base
from app.services.encryption import encryption_service

BENEFICIARY_ROLE_PRIMARY = "PRIMARY"
BENEFICIARY_ROLE_CONTINGENT = "CONTINGENT"
BENEFICIARY_ROLE_SUCCESSOR = "SUCCESSOR"
BENEFICIARY_ROLE_INFORMATIONAL = "INFORMATIONAL"

BENEFICIARY_ROLE_VALUES = {
    BENEFICIARY_ROLE_PRIMARY,
    BENEFICIARY_ROLE_CONTINGENT,
    BENEFICIARY_ROLE_SUCCESSOR,
    BENEFICIARY_ROLE_INFORMATIONAL,
}

TRANSFER_METHOD_BENEFICIARY_DESIGNATION = "BENEFICIARY_DESIGNATION"
TRANSFER_METHOD_WILL = "WILL"
TRANSFER_METHOD_TRUST = "TRUST"
TRANSFER_METHOD_JOINT_OWNERSHIP = "JOINT_OWNERSHIP"
TRANSFER_METHOD_PROBATE = "PROBATE"
TRANSFER_METHOD_OTHER = "OTHER"

TRANSFER_METHOD_VALUES = {
    TRANSFER_METHOD_BENEFICIARY_DESIGNATION,
    TRANSFER_METHOD_WILL,
    TRANSFER_METHOD_TRUST,
    TRANSFER_METHOD_JOINT_OWNERSHIP,
    TRANSFER_METHOD_PROBATE,
    TRANSFER_METHOD_OTHER,
}


class AssetBeneficiary(Base):
    __tablename__ = "asset_beneficiaries"
    __table_args__ = (
        UniqueConstraint("asset_id", "beneficiary_id", name="uq_asset_beneficiary_asset_beneficiary"),
        CheckConstraint("percentage IS NULL OR (percentage >= 0 AND percentage <= 100)", name="ck_asset_beneficiary_percentage_range"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    beneficiary_id = Column(String, ForeignKey("beneficiaries.id", ondelete="CASCADE"), nullable=False, index=True)
    percentage = Column(Numeric(5, 2), nullable=True)
    beneficiary_role = Column(String, nullable=False, default=BENEFICIARY_ROLE_PRIMARY)
    priority_order = Column(Integer, nullable=True)
    transfer_priority = Column(String, nullable=True)
    transfer_method = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    deactivation_reason_encrypted = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    modified_by = Column(String, nullable=True)

    asset = relationship("Asset", back_populates="beneficiaries")
    beneficiary = relationship("Beneficiary", back_populates="assets")

    def set_deactivation_reason(self, reason: str | None) -> None:
        if reason is not None:
            self.deactivation_reason_encrypted = encryption_service.encrypt(reason)

    def get_deactivation_reason(self) -> str | None:
        if self.deactivation_reason_encrypted is None:
            return None
        return encryption_service.decrypt(self.deactivation_reason_encrypted)
