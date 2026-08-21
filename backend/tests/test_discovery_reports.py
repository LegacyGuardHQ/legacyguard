import os
from datetime import datetime, timezone

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.database.connection import Base, SessionLocal, engine
from app.models.discovery import DiscoveryScan, EvidenceFinding
from app.models.document import Document
from app.models.user import User
from app.services.discovery_reports import DiscoveryReportService


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_safe_export_contains_counts_but_not_evidence() -> None:
    db = SessionLocal()
    try:
        user = User(id="report-user", email="report@example.com", password_hash="hash")
        scan = DiscoveryScan(
            id="report-scan",
            user_id=user.id,
            status="COMPLETE",
            documents_processed=1,
            created_at=datetime.now(timezone.utc),
        )
        document = Document(
            id="report-document",
            user_id=user.id,
            document_type="ACCOUNT_STATEMENT",
            document_name="Discovery source",
        )
        db.add(user)
        db.flush()
        db.add_all([scan, document])
        db.flush()
        finding = EvidenceFinding(
            id="report-finding",
            scan_id=scan.id,
            document_id="report-document",
            category="RETIREMENT_INDICATOR",
            confidence_score=85,
            review_status="PENDING_REVIEW",
        )
        finding.set_matched_terms('["secret-term"]')
        finding.set_evidence_excerpt("Sensitive raw evidence")
        db.add(finding)
        db.commit()

        payload = DiscoveryReportService().build_safe_export(db, scan)
        payload_text = str(payload)

        assert payload["scan_id"] == scan.id
        assert payload["total_findings"] == 1
        assert payload["documents_processed"] == 1
        assert payload["categories"] == {"RETIREMENT_INDICATOR": 1}
        assert "secret-term" not in payload_text
        assert "Sensitive raw evidence" not in payload_text
        assert "document" not in payload
    finally:
        db.close()
