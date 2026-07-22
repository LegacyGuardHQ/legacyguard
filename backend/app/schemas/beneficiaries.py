from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.beneficiary import (
    BENEFICIARY_STATUS_ACTIVE,
    BENEFICIARY_VERIFICATION_NEEDS_REVIEW,
    BENEFICIARY_VERIFICATION_OUTDATED,
    BENEFICIARY_VERIFICATION_UNKNOWN,
    BENEFICIARY_VERIFICATION_VERIFIED,
)


class BeneficiaryCreate(BaseModel):
    name: str = Field(..., min_length=1)
    relationship_type: str | None = None
    contact_information: str | None = None
    notes: str | None = None
    verification_status: str = BENEFICIARY_VERIFICATION_UNKNOWN
    review_due_at: datetime | None = None
    is_deceased: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Beneficiary name is required")
        return value.strip()

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(cls, value: str) -> str:
        allowed = {
            BENEFICIARY_VERIFICATION_UNKNOWN,
            BENEFICIARY_VERIFICATION_VERIFIED,
            BENEFICIARY_VERIFICATION_NEEDS_REVIEW,
            BENEFICIARY_VERIFICATION_OUTDATED,
        }
        if value not in allowed:
            raise ValueError("Unsupported beneficiary verification status")
        return value


class BeneficiaryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    relationship_type: str | None = None
    contact_information: str | None = None
    notes: str | None = None
    verification_status: str | None = None
    review_due_at: datetime | None = None
    is_deceased: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.strip():
            raise ValueError("Beneficiary name is required")
        return value.strip()

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        allowed = {
            BENEFICIARY_VERIFICATION_UNKNOWN,
            BENEFICIARY_VERIFICATION_VERIFIED,
            BENEFICIARY_VERIFICATION_NEEDS_REVIEW,
            BENEFICIARY_VERIFICATION_OUTDATED,
        }
        if value not in allowed:
            raise ValueError("Unsupported beneficiary verification status")
        return value


class BeneficiaryListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    relationship_type: str | None = None
    status: str
    verification_status: str
    verified_at: datetime | None = None
    review_due_at: datetime | None = None
    is_deceased: bool
    deceased_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class BeneficiaryResponse(BeneficiaryListResponse):
    contact_information: str | None = None
    notes: str | None = None