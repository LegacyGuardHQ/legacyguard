from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.asset import (
    ASSET_VERIFICATION_CLOSED,
    ASSET_VERIFICATION_NEEDS_REVIEW,
    ASSET_VERIFICATION_UNKNOWN,
    ASSET_VERIFICATION_VERIFIED,
)


class AssetCreate(BaseModel):
    asset_name: str = Field(..., min_length=1)
    asset_category: str = Field(..., min_length=1)
    institution: str | None = None
    description: str | None = None
    estimated_value: float | None = Field(default=None, ge=0)
    ownership_type: str | None = None
    status: str | None = None
    is_verified: bool = False
    verification_status: str = ASSET_VERIFICATION_UNKNOWN

    @field_validator("asset_name")
    @classmethod
    def validate_asset_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Asset name is required")
        return value.strip()

    @field_validator("asset_category")
    @classmethod
    def validate_asset_category(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Asset category is required")
        return value.strip()

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(cls, value: str) -> str:
        allowed = {
            ASSET_VERIFICATION_UNKNOWN,
            ASSET_VERIFICATION_VERIFIED,
            ASSET_VERIFICATION_NEEDS_REVIEW,
            ASSET_VERIFICATION_CLOSED,
        }
        if value not in allowed:
            raise ValueError("Unsupported asset verification status")
        return value


class BeneficiaryCreate(BaseModel):
    name: str = Field(..., min_length=1)
    relationship_type: str = Field(..., min_length=1)
    contact_information: str | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Beneficiary name is required")
        return value.strip()

    @field_validator("relationship_type")
    @classmethod
    def validate_relationship(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Relationship is required")
        return value.strip()


class DocumentCreate(BaseModel):
    document_type: str = Field(..., min_length=1)
    document_name: str = Field(..., min_length=1)
    storage_reference: str | None = None
    encrypted: bool = False
    size_bytes: int | None = Field(default=None, ge=0, le=20 * 1024 * 1024)

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, value: str) -> str:
        allowed = {
            "Insurance Policy",
            "Account Statement",
            "Tax Document",
            "Will",
            "Legal Document",
            "Identification",
            "Other",
        }
        if value not in allowed:
            raise ValueError("Unsupported document type")
        return value
