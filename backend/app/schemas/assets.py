from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.asset import ASSET_VERIFICATION_CLOSED, ASSET_VERIFICATION_NEEDS_REVIEW, ASSET_VERIFICATION_UNKNOWN, ASSET_VERIFICATION_VERIFIED


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
    status: str | None = None
    is_verified: bool = False
    verification_status: str = ASSET_VERIFICATION_UNKNOWN
    details: AssetDetailCreate | None = None

    @field_validator("asset_name", "asset_category")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value is required")
        return value.strip()

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(cls, value: str) -> str:
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
    status: str | None = None
    is_verified: bool | None = None
    verification_status: str | None = None
    details: AssetDetailUpdate | None = None

    @field_validator("asset_name", "asset_category")
    @classmethod
    def validate_optional_required_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Value is required")
        return value.strip() if value is not None else value

    @field_validator("verification_status")
    @classmethod
    def validate_optional_verification_status(cls, value: str | None) -> str | None:
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
    status: str
    is_verified: bool
    verification_status: str
    verified_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AssetResponse(AssetListResponse):
    details: AssetDetailResponse | None = None