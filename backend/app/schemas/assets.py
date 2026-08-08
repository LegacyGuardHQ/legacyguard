from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.asset import (
    ASSET_STATUS_ACTIVE,
    ASSET_STATUS_ARCHIVED,
    ASSET_VERIFICATION_CLOSED,
    ASSET_VERIFICATION_NEEDS_REVIEW,
    ASSET_VERIFICATION_UNKNOWN,
    ASSET_VERIFICATION_VERIFIED,
)

AssetStatus = Literal["Active", "Archived"]
AssetVerificationStatus = Literal["UNKNOWN", "VERIFIED", "NEEDS_REVIEW", "CLOSED"]

assert set(AssetStatus.__args__) == {ASSET_STATUS_ACTIVE, ASSET_STATUS_ARCHIVED}
assert set(AssetVerificationStatus.__args__) == {
    ASSET_VERIFICATION_UNKNOWN,
    ASSET_VERIFICATION_VERIFIED,
    ASSET_VERIFICATION_NEEDS_REVIEW,
    ASSET_VERIFICATION_CLOSED,
}


class AssetDetailCreate(BaseModel):
    account_number: str | None = None
    policy_number: str | None = None
    notes: str | None = None
    claim_instructions: str | None = None


class AssetDetailUpdate(BaseModel):
    account_number: str | None = None
    policy_number: str | None = None
    notes: str | None = None
    claim_instructions: str | None = None


class AssetCreate(BaseModel):
    asset_name: str = Field(..., min_length=1)
    asset_category: str = Field(..., min_length=1)
    institution: str | None = None
    description: str | None = None
    estimated_value: Decimal | None = Field(default=None, ge=0)
    ownership_type: str | None = None
    status: AssetStatus | None = None
    is_verified: bool = False
    verification_status: AssetVerificationStatus = ASSET_VERIFICATION_UNKNOWN
    details: AssetDetailCreate | None = None

    @field_validator("asset_name", "asset_category")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value is required")
        return value.strip()

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(cls, value: AssetVerificationStatus) -> AssetVerificationStatus:
        allowed = {ASSET_VERIFICATION_UNKNOWN, ASSET_VERIFICATION_VERIFIED, ASSET_VERIFICATION_NEEDS_REVIEW, ASSET_VERIFICATION_CLOSED}
        if value not in allowed:
            raise ValueError("Unsupported asset verification status")
        return value


class AssetUpdate(BaseModel):
    asset_name: str | None = None
    asset_category: str | None = None
    institution: str | None = None
    description: str | None = None
    estimated_value: Decimal | None = Field(default=None, ge=0)
    ownership_type: str | None = None
    status: AssetStatus | None = None
    is_verified: bool | None = None
    verification_status: AssetVerificationStatus | None = None
    details: AssetDetailUpdate | None = None

    @field_validator("asset_name", "asset_category")
    @classmethod
    def validate_optional_required_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Value is required")
        return value.strip() if value is not None else value

    @field_validator("verification_status")
    @classmethod
    def validate_optional_verification_status(cls, value: AssetVerificationStatus | None) -> AssetVerificationStatus | None:
        if value is None:
            return value
        allowed = {ASSET_VERIFICATION_UNKNOWN, ASSET_VERIFICATION_VERIFIED, ASSET_VERIFICATION_NEEDS_REVIEW, ASSET_VERIFICATION_CLOSED}
        if value not in allowed:
            raise ValueError("Unsupported asset verification status")
        return value


class AssetDetailResponse(BaseModel):
    account_number: str | None = None
    policy_number: str | None = None
    notes: str | None = None
    claim_instructions: str | None = None


class AssetListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_category: str
    asset_name: str
    institution: str | None = None
    description: str | None = None
    estimated_value: Decimal | None = None
    ownership_type: str | None = None
    status: AssetStatus
    is_verified: bool
    verification_status: AssetVerificationStatus
    verified_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AssetResponse(AssetListResponse):
    details: AssetDetailResponse | None = None
    source_context: str | None = None