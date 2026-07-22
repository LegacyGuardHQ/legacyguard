from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.asset_beneficiary import BENEFICIARY_ROLE_VALUES, TRANSFER_METHOD_VALUES


class AssetBeneficiaryCreate(BaseModel):
    beneficiary_id: str = Field(..., min_length=1)
    beneficiary_role: str
    percentage: Decimal | None = Field(default=None, ge=0, le=100)
    priority_order: int | None = Field(default=None, ge=0)
    transfer_method: str | None = None

    @field_validator("beneficiary_id")
    @classmethod
    def validate_beneficiary_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Beneficiary id is required")
        return value.strip()

    @field_validator("beneficiary_role")
    @classmethod
    def validate_beneficiary_role(cls, value: str) -> str:
        if value not in BENEFICIARY_ROLE_VALUES:
            raise ValueError("Unsupported beneficiary role")
        return value

    @field_validator("transfer_method")
    @classmethod
    def validate_transfer_method(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in TRANSFER_METHOD_VALUES:
            raise ValueError("Unsupported transfer method")
        return value


class AssetBeneficiaryUpdate(BaseModel):
    beneficiary_role: str
    percentage: Decimal | None = Field(default=None, ge=0, le=100)
    priority_order: int | None = Field(default=None, ge=0)
    transfer_method: str | None = None

    @field_validator("beneficiary_role")
    @classmethod
    def validate_beneficiary_role(cls, value: str) -> str:
        if value not in BENEFICIARY_ROLE_VALUES:
            raise ValueError("Unsupported beneficiary role")
        return value

    @field_validator("transfer_method")
    @classmethod
    def validate_transfer_method(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in TRANSFER_METHOD_VALUES:
            raise ValueError("Unsupported transfer method")
        return value


class AssetBeneficiaryDeactivateRequest(BaseModel):
    deactivation_reason: str | None = Field(default=None, max_length=2000)


class AssetBeneficiaryDeactivateResponse(BaseModel):
    id: str
    asset_id: str
    beneficiary_id: str
    is_active: bool
    deactivated_at: datetime


class LinkedBeneficiaryMetadata(BaseModel):
    id: str
    name: str
    relationship_type: str | None = None
    status: str
    verification_status: str
    is_deceased: bool


class AssetBeneficiaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    beneficiary: LinkedBeneficiaryMetadata
    beneficiary_role: str
    percentage: Decimal | None = None
    priority_order: int | None = None
    transfer_method: str | None = None
    created_at: datetime
    updated_at: datetime