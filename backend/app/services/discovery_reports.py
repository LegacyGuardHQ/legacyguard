from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.discovery import DiscoveryScan, EvidenceFinding


@dataclass(frozen=True)
class DiscoveryReportSummary:
    scan_id: str
    status: str
    total_findings: int
    categories: dict[str, int]
    review_statuses: dict[str, int]


class DiscoveryReportService:
    def build_summary(self, db: Session, scan: DiscoveryScan) -> DiscoveryReportSummary:
        findings = db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == scan.id).all()
        categories: dict[str, int] = {}
        review_statuses: dict[str, int] = {}

        for finding in findings:
            categories[finding.category] = categories.get(finding.category, 0) + 1
            review_statuses[finding.review_status] = review_statuses.get(finding.review_status, 0) + 1

        return DiscoveryReportSummary(
            scan_id=scan.id,
            status=scan.status,
            total_findings=len(findings),
            categories=categories,
            review_statuses=review_statuses,
        )

    def build_safe_export(self, db: Session, scan: DiscoveryScan) -> dict[str, Any]:
        """Build a serialization-ready report without evidence or document data."""
        summary = self.build_summary(db, scan)
        payload: dict[str, Any] = asdict(summary)
        payload["documents_processed"] = scan.documents_processed
        payload["created_at"] = scan.created_at.isoformat() if scan.created_at else None
        payload["completed_at"] = scan.completed_at.isoformat() if scan.completed_at else None
        return payload
