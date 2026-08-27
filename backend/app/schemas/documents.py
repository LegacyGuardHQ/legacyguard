from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.document import (
    DOCUMENT_STATUS_ACTIVE,
    DOCUMENT_STATUS_ARCHIVED,
    DOCUMENT_STATUS_DELETED_PENDING_PURGE,
    DOCUMENT_STATUS_REPLACED,
    DOCUMENT_TYPE_VALUES,
    DOCUMENT_VERIFICATION_EXPIRED,
    DOCUMENT_VERIFICATION_NEEDS_REVIEW,
    DOCUMENT_VERIFICATION_REPLACED,
    DOCUMENT_VERIFICATION_UNKNOWN,
    DOCUMENT_VERIFICATION_VERIFIED,
)
from app.services.document_validation import MAX_DOCUMENT_BYTES, normalize_display_filename, validate_extension_and_mime

DocumentUploadDiscoveryScanStatus = Literal[
    "PENDING",
    "RUNNING",
    "COMPLETE",
    "COMPLETED_WITH_WARNINGS",
    "FAILED",
]

DocumentStatus = Literal[
    "ACTIVE",
    "ARCHIVED",
    "REPLACED",
    "DELETED_PENDING_PURGE",
]

DocumentVerificationStatus = Literal[
    "UNKNOWN",
    "VERIFIED",
    "NEEDS_REVIEW",
    "EXPIRED",
    "REPLACED",
]

DocumentUploadStatus = Literal["COMPLETED"]

assert set(DocumentStatus.__args__) == {
    DOCUMENT_STATUS_ACTIVE,
    DOCUMENT_STATUS_ARCHIVED,
    DOCUMENT_STATUS_REPLACED,
    DOCUMENT_STATUS_DELETED_PENDING_PURGE,
}
assert set(DocumentVerificationStatus.__args__) == {
    DOCUMENT_VERIFICATION_UNKNOWN,
    DOCUMENT_VERIFICATION_VERIFIED,
    DOCUMENT_VERIFICATION_NEEDS_REVIEW,
    DOCUMENT_VERIFICATION_EXPIRED,
    DOCUMENT_VERIFICATION_REPLACED,
}


class DocumentCreate(BaseModel):
    asset_id: str | None = Field(default=None, max_length=64)
    beneficiary_id: str | None = Field(default=None, max_length=64)
    document_type: str = Field(..., max_length=100)
    document_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    original_filename: str | None = Field(default=None, max_length=255)
    mime_type: str | None = Field(default=None, max_length=255)
    file_size: int | None = Field(default=None, ge=0, le=MAX_DOCUMENT_BYTES)
    effective_date: datetime | None = None
    expiration_date: datetime | None = None
    review_due_at: datetime | None = None
    version_number: int = Field(default=1, ge=1, le=2_147_483_647)

    model_config = ConfigDict(extra="forbid")

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, value: str) -> str:
        if value not in DOCUMENT_TYPE_VALUES:
            raise ValueError("Unsupported document type")
        return value

    @field_validator("document_name")
    @classmethod
    def validate_document_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Document name is required")
        return value.strip()

    @model_validator(mode="after")
    def validate_metadata(self) -> "DocumentCreate":
        if self.original_filename is not None:
            self.original_filename = normalize_display_filename(self.original_filename)
        if self.original_filename is not None and self.mime_type is not None:
            validate_extension_and_mime(self.original_filename, self.mime_type)
        if self.effective_date and self.expiration_date and self.expiration_date < self.effective_date:
            raise ValueError("Expiration date cannot be before effective date")
        return self


class DocumentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str | None = None
    beneficiary_id: str | None = None
    document_type: str
    document_name: str
    original_filename: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    status: DocumentStatus
    verification_status: DocumentVerificationStatus
    verified_at: datetime | None = None
    review_due_at: datetime | None = None
    effective_date: datetime | None = None
    expiration_date: datetime | None = None
    archived_at: datetime | None = None
    version_number: int
    created_at: datetime
    updated_at: datetime


class DocumentResponse(DocumentListResponse):
    description: str | None = None


class DocumentUploadDiscoveryScanResponse(BaseModel):
    scan_id: str
    status: DocumentUploadDiscoveryScanStatus


class DocumentUploadResponse(BaseModel):
    id: str
    document_type: str
    document_name: str
    original_filename: str
    mime_type: str
    file_size: int
    upload_status: DocumentUploadStatus
    updated_at: datetime
    discovery_scan: DocumentUploadDiscoveryScanResponse | None = None
