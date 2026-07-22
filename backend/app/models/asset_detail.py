import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base
from app.services.encryption import encryption_service


class AssetDetail(Base):
    __tablename__ = "asset_details"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    account_number_encrypted = Column(Text, nullable=True)
    policy_number_encrypted = Column(Text, nullable=True)
    login_information_reference = Column(Text, nullable=True)
    contact_information = Column(Text, nullable=True)
    notes_encrypted = Column(Text, nullable=True)
    claim_instructions_encrypted = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    modified_by = Column(String, nullable=True)

    asset = relationship("Asset", back_populates="details")

    def set_encrypted_fields(
        self,
        account_number: str | None = None,
        policy_number: str | None = None,
        notes: str | None = None,
        claim_instructions: str | None = None,
    ) -> None:
        if account_number is not None:
            self.account_number_encrypted = encryption_service.encrypt(account_number)
        if policy_number is not None:
            self.policy_number_encrypted = encryption_service.encrypt(policy_number)
        if notes is not None:
            self.notes_encrypted = encryption_service.encrypt(notes)
        if claim_instructions is not None:
            self.claim_instructions_encrypted = encryption_service.encrypt(claim_instructions)

    def get_decrypted_value(self, field_name: str) -> str | None:
        value = getattr(self, field_name)
        if value is None:
            return None
        return encryption_service.decrypt(value)
