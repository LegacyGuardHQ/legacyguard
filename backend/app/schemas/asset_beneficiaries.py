from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.asset_beneficiary import (
    BENEFICIARY_ROLE_CONTINGENT,
    BENEFICIARY_ROLE_INFORMATIONAL,
    BENEFICIARY_ROLE_PRIMARY,
    BENEFICIARY_ROLE_SUCCESSOR,
    BENEFICIARY_ROLE_VALUES,
    TRANSFER_METHOD_BENEFICIARY_DESIGNATION,
    TRANSFER_METHOD_JOINT_OWNERSHIP,
    TRANSFER_METHOD_OTHER,
    TRANSFER_METHOD_PROBATE,
    TRANSFER_METHOD_TRUST,
    TRANSFER_METHOD_VALUES,
    TRANSFER_METHOD_WILL,
)
from app.models.beneficiary import (
    BENEFICIARY_STATUS_ACTIVE,
    BENEFICIARY_STATUS_ARCHIVED,
    BENEFICIARY_STATUS_DECEASED,
    BENEFICIARY_VERIFICATION_NEEDS_REVIEW,
    BENEFICIARY_VERIFICATION_OUTDATED,
    BENEFICIARY_VERIFICATION_UNKNOWN,
    BENEFICIARY_VERIFICATION_VERIFIED,
)

BeneficiaryRole = Literal["PRIMARY", "CONTINGENT", "SUCCESSOR", "INFORMATIONAL"]
TransferMethod = Literal[
    "BENEFICIARY_DESIGNATION",
    "WILL",
    "TRUST",
    "JOINT_OWNERSHIP",
    "PROBATE",
    "OTHER",
]
LinkedBeneficiaryStatus = Literal["Active", "Archived", "Deceased"]
LinkedBeneficiaryVerificationStatus = Literal["UNKNOWN", "VERIFIED", "NEEDS_REVIEW", "OUTDATED"]

assert set(BeneficiaryRole.__args__) == {
    BENEFICIARY_ROLE_PRIMARY,
    BENEFICIARY_ROLE_CONTINGENT,
    BENEFICIARY_ROLE_SUCCESSOR,
    BENEFICIARY_ROLE_INFORMATIONAL,
}
assert set(TransferMethod.__args__) == {
    TRANSFER_METHOD_BENEFICIARY_DESIGNATION,
    TRANSFER_METHOD_WILL,
    TRANSFER_METHOD_TRUST,
    TRANSFER_METHOD_JOINT_OWNERSHIP,
    TRANSFER_METHOD_PROBATE,
    TRANSFER_METHOD_OTHER,
}
assert set(LinkedBeneficiaryStatus.__args__) == {
    BENEFICIARY_STATUS_ACTIVE,
    BENEFICIARY_STATUS_ARCHIVED,
    BENEFICIARY_STATUS_DECEASED,
}
assert set(LinkedBeneficiaryVerificationStatus.__args__) == {
    BENEFICIARY_VERIFICATION_UNKNOWN,
    BENEFICIARY_VERIFICATION_VERIFIED,
    BENEFICIARY_VERIFICATION_NEEDS_REVIEW,
    BENEFICIARY_VERIFICATION_OUTDATED,
}


class AssetBeneficiaryCreate(BaseModel):
    beneficiary_id: str = Field(..., min_length=1)
    beneficiary_role: BeneficiaryRole
    percentage: Decimal | None = Field(default=None, ge=0, le=100)
    priority_order: int | None = Field(default=None, ge=0)
    transfer_method: TransferMethod | None = None

    @field_validator("beneficiary_id")
    @classmethod
    def validate_beneficiary_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Beneficiary id is required")
        return value.strip()

    @field_validator("beneficiary_role")
    @classmethod
    def validate_beneficiary_role(cls, value: BeneficiaryRole) -> BeneficiaryRole:
        if value not in BENEFICIARY_ROLE_VALUES:
            raise ValueError("Unsupported beneficiary role")
        return value

    @field_validator("transfer_method")
    @classmethod
    def validate_transfer_method(cls, value: TransferMethod | None) -> TransferMethod | None:
        if value is None:
            return value
        if value not in TRANSFER_METHOD_VALUES:
            raise ValueError("Unsupported transfer method")
        return value


class AssetBeneficiaryUpdate(BaseModel):
    beneficiary_role: BeneficiaryRole
    percentage: Decimal | None = Field(default=None, ge=0, le=100)
    priority_order: int | None = Field(default=None, ge=0)
    transfer_method: TransferMethod | None = None

    @field_validator("beneficiary_role")
    @classmethod
    def validate_beneficiary_role(cls, value: BeneficiaryRole) -> BeneficiaryRole:
        if value not in BENEFICIARY_ROLE_VALUES:
            raise ValueError("Unsupported beneficiary role")
        return value

    @field_validator("transfer_method")
    @classmethod
    def validate_transfer_method(cls, value: TransferMethod | None) -> TransferMethod | None:
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
    status: LinkedBeneficiaryStatus
    verification_status: LinkedBeneficiaryVerificationStatus
    is_deceased: bool


class AssetBeneficiaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    beneficiary: LinkedBeneficiaryMetadata
    beneficiary_role: BeneficiaryRole
    percentage: Decimal | None = None
    priority_order: int | None = None
    transfer_method: TransferMethod | None = None
    created_at: datetime
    updated_at: datetime