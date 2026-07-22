from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.discovery import EVIDENCE_REVIEW_STATUS_CONFIRMED, EVIDENCE_REVIEW_STATUS_DISMISSED


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


class DiscoveryScanSummaryResponse(BaseModel):
    scan_id: str
    status: str
    documents_processed: int
    created_at: datetime
    completed_at: datetime | None = None


class DiscoveryReportSummaryResponse(BaseModel):
    scan_id: str
    status: str
    total_findings: int
    categories: dict[str, int]
    review_statuses: dict[str, int]


class EvidenceFindingResponse(BaseModel):
    finding_id: str
    category: str
    confidence_score: float
    review_status: str
    created_at: datetime


class EvidenceFindingReviewRequest(BaseModel):
    review_status: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("review_status")
    @classmethod
    def validate_review_status(cls, value: str) -> str:
        if value not in {EVIDENCE_REVIEW_STATUS_CONFIRMED, EVIDENCE_REVIEW_STATUS_DISMISSED}:
            raise ValueError("Unsupported review status")
        return value