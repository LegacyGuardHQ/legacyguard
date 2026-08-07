from datetime import datetime
from typing import Generic, List, Literal, TypeVar
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.assets import AssetDetailCreate

from app.models.discovery import (
    DISCOVERY_SCAN_STATUS_COMPLETE,
    DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS,
    DISCOVERY_SCAN_STATUS_FAILED,
    DISCOVERY_SCAN_STATUS_PENDING,
    DISCOVERY_SCAN_STATUS_RUNNING,
    EVIDENCE_REVIEW_STATUS_CONFIRMED,
    EVIDENCE_REVIEW_STATUS_DISMISSED,
    EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
)
from app.models.discovery_scan_document import (
    DISCOVERY_DOCUMENT_STATUS_COMPLETED,
    DISCOVERY_DOCUMENT_STATUS_FAILED,
    DISCOVERY_DOCUMENT_STATUS_PENDING,
    DISCOVERY_DOCUMENT_STATUS_PROCESSING,
    DISCOVERY_DOCUMENT_STATUS_SKIPPED,
    DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED,
    DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION,
)

T = TypeVar('T')

DiscoveryDocumentStatus = Literal[
    "PENDING",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    "SKIPPED",
]
DiscoveryDocumentWarning = Literal[
    "PROCESSING_FAILED",
    "UNSUPPORTED_EXTRACTION",
]

DiscoveryLifecycleState = Literal[
    "QUEUED",
    "RUNNING",
    "COMPLETED",
    "COMPLETED_WITH_WARNINGS",
    "FAILED",
]

DiscoveryProcessingOutcome = Literal[
    "QUEUED",
    "IN_PROGRESS",
    "COMPLETED",
    "COMPLETED_WITH_WARNINGS",
    "FAILED",
    "RECOVERED",
    "RECOVERED_AND_COMPLETED",
]

# Keep the public contract synchronized with the model's controlled values.
assert set(DiscoveryDocumentStatus.__args__) == {
    DISCOVERY_DOCUMENT_STATUS_PENDING,
    DISCOVERY_DOCUMENT_STATUS_PROCESSING,
    DISCOVERY_DOCUMENT_STATUS_COMPLETED,
    DISCOVERY_DOCUMENT_STATUS_FAILED,
    DISCOVERY_DOCUMENT_STATUS_SKIPPED,
}
assert set(DiscoveryDocumentWarning.__args__) == {
    DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED,
    DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION,
}

class DiscoveryScanDocumentSchema(BaseModel):
    id: str
    scan_id: str
    document_id: str
    status: str
    warning_code: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscoveryScanCreate(BaseModel):
    document_ids: list[str] = Field(..., min_length=1)
    model_config = ConfigDict(extra="forbid")


class DiscoveryScanResponse(BaseModel):
    scan_id: str
    status: str
    created_at: datetime


class DiscoveryScanStatusResponse(DiscoveryScanResponse):
    documents_processed: int
    completed_at: datetime | None = None
    lifecycle_state: DiscoveryLifecycleState
    recovered_from_stale: bool = Field(default=False, description="Whether the scan was recovered from a stale running state.")
    recovered_at: datetime | None = None
    processing_outcome: DiscoveryProcessingOutcome = Field(
        default="IN_PROGRESS",
        description="Controlled processing outcome for the current scan state.",
    )
    processing_outcome_message: str = Field(default="Processing is active", description="Privacy-safe user-facing processing outcome message.")


class DiscoveryScanSummaryResponse(BaseModel):
    scan_id: str
    status: str
    documents_processed: int
    created_at: datetime
    completed_at: datetime | None = None


class DiscoveryScanStatusCounts(BaseModel):
    PENDING: int = Field(default=0, ge=0, description="Scans queued but not yet running.")
    RUNNING: int = Field(default=0, ge=0, description="Scans currently being processed.")
    COMPLETE: int = Field(default=0, ge=0, description="Scans completed without recorded warnings.")
    COMPLETED_WITH_WARNINGS: int = Field(
        default=0,
        ge=0,
        description="Scans completed with one or more controlled processing warnings.",
    )
    FAILED: int = Field(default=0, ge=0, description="Scans that ended because processing failed.")


class EvidenceFindingReviewStatusCounts(BaseModel):
    PENDING_REVIEW: int = Field(default=0, ge=0, description="Findings awaiting human review.")
    CONFIRMED: int = Field(default=0, ge=0, description="Findings confirmed through human review.")
    DISMISSED: int = Field(default=0, ge=0, description="Findings dismissed through human review.")


# Keep aggregate response keys synchronized with the model's controlled values.
assert set(DiscoveryScanStatusCounts.model_fields) == {
    DISCOVERY_SCAN_STATUS_PENDING,
    DISCOVERY_SCAN_STATUS_RUNNING,
    DISCOVERY_SCAN_STATUS_COMPLETE,
    DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS,
    DISCOVERY_SCAN_STATUS_FAILED,
}
assert set(EvidenceFindingReviewStatusCounts.model_fields) == {
    EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
    EVIDENCE_REVIEW_STATUS_CONFIRMED,
    EVIDENCE_REVIEW_STATUS_DISMISSED,
}


class DiscoveryDashboardResponse(BaseModel):
    """Owner-scoped operational counts without document content or evidence."""

    total_scans: int = Field(ge=0, description="Total discovery scans owned by the current user.")
    scans_by_status: DiscoveryScanStatusCounts = Field(
        description="Owner-scoped scan totals for every supported scan status."
    )
    total_findings: int = Field(ge=0, description="Total discovery findings owned by the current user.")
    pending_reviews: int = Field(
        ge=0,
        description="Findings owned by the current user that require human review.",
    )
    findings_by_category: dict[str, int] = Field(
        description="Counts by controlled finding category; no evidence text is included."
    )
    findings_by_review_status: EvidenceFindingReviewStatusCounts = Field(
        description="Owner-scoped finding totals for every supported human-review status."
    )
    recent_scans: list[DiscoveryScanSummaryResponse] = Field(
        description="At most five most recently created owner-scoped scans."
    )


class DiscoveryScanDocumentResponse(BaseModel):
    """Safe scan-document metadata; never includes content or storage metadata."""

    document_id: str
    document_name: str
    document_type: str
    status: DiscoveryDocumentStatus = Field(
        description=(
            "Discovery processing state: PENDING is queued, PROCESSING is active, COMPLETED finished "
            "successfully, SKIPPED identifies a known non-fatal extraction limitation, and FAILED "
            "identifies a processing failure."
        )
    )
    warning_code: DiscoveryDocumentWarning | None = Field(
        default=None,
        description=(
            "Controlled reason a document was not fully processed: PROCESSING_FAILED identifies a "
            "processing failure and UNSUPPORTED_EXTRACTION identifies content the current extractor "
            "cannot process. Null means no warning was recorded."
        ),
    )
    created_at: datetime


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total_count: int
    page: int
    page_size: int


class PaginatedDiscoveryScanResponse(BaseModel):
    items: list[DiscoveryScanSummaryResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class DiscoveryReportSummaryResponse(BaseModel):
    scan_id: str
    status: str
    total_findings: int
    categories: dict[str, int]
    review_statuses: dict[str, int]


class DiscoverySafeReportResponse(DiscoveryReportSummaryResponse):
    documents_processed: int
    created_at: datetime
    completed_at: datetime | None = None


class EvidenceFindingResponse(BaseModel):
    finding_id: str
    category: str
    confidence_score: float = Field(
        description=(
            "Rule-based detection signal strength. It is not a probability, certainty, account "
            "ownership determination, financial verification, or guarantee that an asset exists."
        )
    )
    review_status: str
    created_at: datetime


class EvidenceFindingDetailResponse(EvidenceFindingResponse):
    """Safe finding context without matched terms or decrypted evidence excerpts."""

    scan_id: str
    document_id: str
    document_name: str
    document_type: str


class PaginatedEvidenceFindingResponse(BaseModel):
    items: list[EvidenceFindingResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class ManualAssetConversionRequest(BaseModel):
    asset_name: str = Field(..., min_length=1)
    asset_category: str = Field(..., min_length=1)
    institution: str | None = None
    description: str | None = None
    estimated_value: Decimal | None = Field(default=None, ge=0)
    ownership_type: str | None = None
    details: AssetDetailCreate | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("asset_name", "asset_category")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value is required")
        return value.strip()


class EvidenceFindingReviewRequest(BaseModel):
    review_status: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("review_status")
    @classmethod
    def validate_review_status(cls, value: str) -> str:
        if value not in {
            EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
            EVIDENCE_REVIEW_STATUS_CONFIRMED,
            EVIDENCE_REVIEW_STATUS_DISMISSED,
        }:
            raise ValueError("Unsupported review status")
        return value

