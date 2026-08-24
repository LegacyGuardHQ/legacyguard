from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base
from app.services.encryption import encryption_service

DOCUMENT_TYPE_WILL = "WILL"
DOCUMENT_TYPE_TRUST = "TRUST"
DOCUMENT_TYPE_LIFE_INSURANCE_POLICY = "LIFE_INSURANCE_POLICY"
DOCUMENT_TYPE_BENEFICIARY_FORM = "BENEFICIARY_FORM"
DOCUMENT_TYPE_ACCOUNT_STATEMENT = "ACCOUNT_STATEMENT"
DOCUMENT_TYPE_RETIREMENT_DOCUMENT = "RETIREMENT_DOCUMENT"
DOCUMENT_TYPE_DEED = "DEED"
DOCUMENT_TYPE_VEHICLE_TITLE = "VEHICLE_TITLE"
DOCUMENT_TYPE_TAX_DOCUMENT = "TAX_DOCUMENT"
DOCUMENT_TYPE_IDENTIFICATION = "IDENTIFICATION"
DOCUMENT_TYPE_POWER_OF_ATTORNEY = "POWER_OF_ATTORNEY"
DOCUMENT_TYPE_HEALTHCARE_DIRECTIVE = "HEALTHCARE_DIRECTIVE"
DOCUMENT_TYPE_EMPLOYER_BENEFIT_DOCUMENT = "EMPLOYER_BENEFIT_DOCUMENT"
DOCUMENT_TYPE_GOVERNMENT_BENEFIT_DOCUMENT = "GOVERNMENT_BENEFIT_DOCUMENT"
DOCUMENT_TYPE_DIGITAL_ASSET_INSTRUCTIONS = "DIGITAL_ASSET_INSTRUCTIONS"
DOCUMENT_TYPE_OTHER = "OTHER"

DOCUMENT_TYPE_VALUES = {
    DOCUMENT_TYPE_WILL,
    DOCUMENT_TYPE_TRUST,
    DOCUMENT_TYPE_LIFE_INSURANCE_POLICY,
    DOCUMENT_TYPE_BENEFICIARY_FORM,
    DOCUMENT_TYPE_ACCOUNT_STATEMENT,
    DOCUMENT_TYPE_RETIREMENT_DOCUMENT,
    DOCUMENT_TYPE_DEED,
    DOCUMENT_TYPE_VEHICLE_TITLE,
    DOCUMENT_TYPE_TAX_DOCUMENT,
    DOCUMENT_TYPE_IDENTIFICATION,
    DOCUMENT_TYPE_POWER_OF_ATTORNEY,
    DOCUMENT_TYPE_HEALTHCARE_DIRECTIVE,
    DOCUMENT_TYPE_EMPLOYER_BENEFIT_DOCUMENT,
    DOCUMENT_TYPE_GOVERNMENT_BENEFIT_DOCUMENT,
    DOCUMENT_TYPE_DIGITAL_ASSET_INSTRUCTIONS,
    DOCUMENT_TYPE_OTHER,
}

DOCUMENT_STATUS_ACTIVE = "ACTIVE"
DOCUMENT_STATUS_ARCHIVED = "ARCHIVED"
DOCUMENT_STATUS_REPLACED = "REPLACED"
DOCUMENT_STATUS_DELETED_PENDING_PURGE = "DELETED_PENDING_PURGE"

DOCUMENT_VERIFICATION_UNKNOWN = "UNKNOWN"
DOCUMENT_VERIFICATION_VERIFIED = "VERIFIED"
DOCUMENT_VERIFICATION_NEEDS_REVIEW = "NEEDS_REVIEW"
DOCUMENT_VERIFICATION_EXPIRED = "EXPIRED"
DOCUMENT_VERIFICATION_REPLACED = "REPLACED"

DOCUMENT_STORAGE_PENDING = "PENDING"
DOCUMENT_STORAGE_STORED = "STORED"
DOCUMENT_STORAGE_FAILED = "FAILED"
DOCUMENT_STORAGE_STATE_VALUES = {
    DOCUMENT_STORAGE_PENDING,
    DOCUMENT_STORAGE_STORED,
    DOCUMENT_STORAGE_FAILED,
}
DOCUMENT_STORAGE_BACKEND_LOCAL = "LOCAL"
DOCUMENT_STORAGE_BACKEND_OBJECT = "OBJECT"
LEGACY_DOCUMENT_MASTER_KEY_ID = "legacy-current-v1"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "storage_state IN ('PENDING', 'STORED', 'FAILED')",
            name="ck_documents_storage_state",
        ),
    )

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    beneficiary_id = Column(String, ForeignKey("beneficiaries.id", ondelete="SET NULL"), nullable=True, index=True)
    document_type = Column(String, nullable=False, index=True)
    document_name = Column(String, nullable=False, index=True)
    description_encrypted = Column(Text, nullable=True)
    original_filename = Column(String, nullable=True)
    mime_type = Column(String, nullable=True, index=True)
    file_size = Column(Integer, nullable=True)
    checksum_sha256 = Column(String, nullable=True, index=True)
    content_encryption_version = Column(String, nullable=True)
    encryption_key_reference_encrypted = Column(Text, nullable=True)
    storage_reference_encrypted = Column(Text, nullable=True)
    storage_backend = Column(String, nullable=False, default=DOCUMENT_STORAGE_BACKEND_LOCAL, index=True)
    storage_provider_version = Column(String, nullable=True)
    storage_state = Column(String, nullable=False, default=DOCUMENT_STORAGE_PENDING, index=True)
    storage_state_updated_at = Column(DateTime(timezone=True), nullable=True)
    storage_error_code = Column(String, nullable=True)
    upload_attempt_id = Column(String, nullable=True, unique=True, index=True)
    ciphertext_sha256 = Column(String(length=64), nullable=True)
    ciphertext_size = Column(Integer, nullable=True)
    master_key_id = Column(String, nullable=True, index=True)
    # Deprecated: retained temporarily for migration compatibility only. New code must use storage_reference_encrypted.
    storage_reference = Column(Text, nullable=True)
    encrypted = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default=DOCUMENT_STATUS_ACTIVE, index=True)
    verification_status = Column(String, nullable=False, default=DOCUMENT_VERIFICATION_UNKNOWN, index=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    review_due_at = Column(DateTime(timezone=True), nullable=True)
    effective_date = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by_document_id = Column(String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    version_number = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    modified_by = Column(String, nullable=True)

    user = relationship("User", back_populates="documents")
    asset = relationship("Asset", back_populates="documents")
    beneficiary = relationship("Beneficiary", back_populates="documents")
    replaced_by_document = relationship("Document", remote_side=[id])

    def set_storage_reference(self, storage_reference: str | None) -> None:
        if storage_reference is not None:
            self.storage_reference_encrypted = encryption_service.encrypt(storage_reference)
        self.storage_reference = None

    def get_storage_reference(self) -> str | None:
        if self.storage_reference_encrypted is None:
            return None
        return encryption_service.decrypt(self.storage_reference_encrypted)

    def set_description(self, description: str | None) -> None:
        if description is not None:
            self.description_encrypted = encryption_service.encrypt(description)

    def get_description(self) -> str | None:
        if self.description_encrypted is None:
            return None
        return encryption_service.decrypt(self.description_encrypted)

    def set_encryption_key_reference(self, key_reference: str | None) -> None:
        if key_reference is not None:
            self.encryption_key_reference_encrypted = encryption_service.encrypt(key_reference)

    def get_encryption_key_reference(self) -> str | None:
        if self.encryption_key_reference_encrypted is None:
            return None
        return encryption_service.decrypt(self.encryption_key_reference_encrypted)
