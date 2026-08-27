from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base
from app.services.encryption import encryption_service

BENEFICIARY_STATUS_ACTIVE = "Active"
BENEFICIARY_STATUS_ARCHIVED = "Archived"
BENEFICIARY_STATUS_DECEASED = "Deceased"

BENEFICIARY_VERIFICATION_UNKNOWN = "UNKNOWN"
BENEFICIARY_VERIFICATION_VERIFIED = "VERIFIED"
BENEFICIARY_VERIFICATION_NEEDS_REVIEW = "NEEDS_REVIEW"
BENEFICIARY_VERIFICATION_OUTDATED = "OUTDATED"


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    relationship_type = Column(String, nullable=True)
    contact_information_encrypted = Column(Text, nullable=True)
    notes_encrypted = Column(Text, nullable=True)
    status = Column(String, nullable=False, default=BENEFICIARY_STATUS_ACTIVE)
    verification_status = Column(String, nullable=False, default=BENEFICIARY_VERIFICATION_UNKNOWN)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    review_due_at = Column(DateTime(timezone=True), nullable=True)
    is_deceased = Column(Boolean, nullable=False, default=False)
    deceased_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    modified_by = Column(String, nullable=True)

    user = relationship("User", back_populates="beneficiaries")
    assets = relationship("AssetBeneficiary", back_populates="beneficiary", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="beneficiary")

    def set_encrypted_fields(self, contact_information: str | None = None, notes: str | None = None) -> None:
        if contact_information is not None:
            self.contact_information_encrypted = encryption_service.encrypt(contact_information)
        if notes is not None:
            self.notes_encrypted = encryption_service.encrypt(notes)

    def get_decrypted_value(self, field_name: str) -> str | None:
        value = getattr(self, field_name)
        if value is None:
            return None
        return encryption_service.decrypt(value)
