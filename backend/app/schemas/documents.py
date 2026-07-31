from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.document import DOCUMENT_TYPE_VALUES
from app.services.document_validation import normalize_display_filename, validate_extension_and_mime


class DocumentCreate(BaseModel):
    asset_id: str | None = None
    beneficiary_id: str | None = None
    document_type: str
    document_name: str = Field(..., min_length=1)
    description: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    file_size: int | None = Field(default=None, ge=0)
    effective_date: datetime | None = None
    expiration_date: datetime | None = None
    review_due_at: datetime | None = None
    version_number: int = Field(default=1, ge=1)

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
    status: str
    verification_status: str
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
    status: str


class DocumentUploadResponse(BaseModel):
    id: str
    document_type: str
    document_name: str
    original_filename: str
    mime_type: str
    file_size: int
    checksum_sha256: str
    upload_status: str
    updated_at: datetime
    discovery_scan: DocumentUploadDiscoveryScanResponse | None = None
