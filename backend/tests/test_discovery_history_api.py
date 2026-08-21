import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.database.connection import SessionLocal
from app.main import app
from app.models.discovery import EVIDENCE_REVIEW_STATUS_CONFIRMED, EVIDENCE_REVIEW_STATUS_DISMISSED, EVIDENCE_REVIEW_STATUS_PENDING_REVIEW, DiscoveryScan, EvidenceFinding
from app.models.document import Document
from app.services.rate_limit import rate_limiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    from app.database.connection import Base, engine

    rate_limiter.reset_all()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    rate_limiter.reset_all()


def _token(email: str) -> str:
    password = "StrongPass123!"
    assert client.post("/auth/register", json={"email": email, "password": password}).status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def _user_id(token: str) -> str:
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]


def _seed_scan(user_id: str, scan_id: str, created_at: datetime | None = None) -> None:
    db = SessionLocal()
    try:
        db.add(DiscoveryScan(id=scan_id, user_id=user_id, status="COMPLETE", documents_processed=1, created_at=created_at or datetime.now(timezone.utc)))
        db.commit()
    finally:
        db.close()


def _seed_finding(scan_id: str, finding_id: str, category: str, review_status: str) -> None:
    db = SessionLocal()
    try:
        scan = db.query(DiscoveryScan).filter(DiscoveryScan.id == scan_id).one()
        document_id = f"doc-{finding_id}"
        db.add(
            Document(
                id=document_id,
                user_id=scan.user_id,
                document_type="ACCOUNT_STATEMENT",
                document_name="Discovery source",
            )
        )
        db.flush()
        finding = EvidenceFinding(id=finding_id, scan_id=scan_id, document_id=document_id, category=category, confidence_score=85, review_status=review_status)
        finding.set_matched_terms('["secret-term"]')
        finding.set_evidence_excerpt("Sensitive raw evidence")
        db.add(finding)
        db.commit()
    finally:
        db.close()


def test_user_sees_own_scans_newest_first() -> None:
    token = _token("history@example.com")
    user_id = _user_id(token)
    _seed_scan(user_id, "old-scan", datetime.now(timezone.utc) - timedelta(days=1))
    _seed_scan(user_id, "new-scan", datetime.now(timezone.utc))

    response = client.get("/discovery/scans", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert [scan["scan_id"] for scan in payload["items"]] == ["new-scan", "old-scan"]
    assert payload["total_count"] == 2
    assert payload["page"] == 1


def test_user_cannot_see_another_users_scans() -> None:
    owner_token = _token("owner-history@example.com")
    other_token = _token("other-history@example.com")
    _seed_scan(_user_id(owner_token), "owner-scan")

    response = client.get("/discovery/scans", headers={"Authorization": f"Bearer {other_token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total_count"] == 0


def test_summary_counts_are_correct() -> None:
    token = _token("summary@example.com")
    user_id = _user_id(token)
    _seed_scan(user_id, "summary-scan")
    _seed_finding("summary-scan", "finding-1", "RETIREMENT_INDICATOR", EVIDENCE_REVIEW_STATUS_PENDING_REVIEW)
    _seed_finding("summary-scan", "finding-2", "RETIREMENT_INDICATOR", EVIDENCE_REVIEW_STATUS_CONFIRMED)
    _seed_finding("summary-scan", "finding-3", "INSURANCE_INDICATOR", EVIDENCE_REVIEW_STATUS_DISMISSED)

    response = client.get("/discovery/scans/summary-scan/summary", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_findings"] == 3
    assert payload["categories"] == {"RETIREMENT_INDICATOR": 2, "INSURANCE_INDICATOR": 1}
    assert payload["review_statuses"] == {"PENDING_REVIEW": 1, "CONFIRMED": 1, "DISMISSED": 1}


def test_history_and_summary_exclude_sensitive_fields() -> None:
    token = _token("sensitive-history@example.com")
    user_id = _user_id(token)
    _seed_scan(user_id, "safe-scan")
    _seed_finding("safe-scan", "finding-safe", "RETIREMENT_INDICATOR", EVIDENCE_REVIEW_STATUS_PENDING_REVIEW)

    history_payload = client.get("/discovery/scans", headers={"Authorization": f"Bearer {token}"}).json()["items"][0]
    summary_payload = client.get("/discovery/scans/safe-scan/summary", headers={"Authorization": f"Bearer {token}"}).json()

    for payload in (history_payload, summary_payload):
        assert "matched_terms" not in payload
        assert "matched_terms_encrypted" not in payload
        assert "evidence_excerpt" not in payload
        assert "evidence_excerpt_encrypted" not in payload
        assert "documents" not in payload
        assert "evidence" not in payload


def test_reports_do_not_contain_raw_evidence() -> None:
    token = _token("raw-report@example.com")
    user_id = _user_id(token)
    _seed_scan(user_id, "raw-scan")
    _seed_finding("raw-scan", "finding-raw", "RETIREMENT_INDICATOR", EVIDENCE_REVIEW_STATUS_PENDING_REVIEW)

    payload_text = str(client.get("/discovery/scans/raw-scan/summary", headers={"Authorization": f"Bearer {token}"}).json())

    assert "Sensitive raw evidence" not in payload_text
    assert "secret-term" not in payload_text

def test_scan_history_pagination() -> None:
    token = _token("pagination@example.com")
    user_id = _user_id(token)
    for index in range(5):
        _seed_scan(
            user_id,
            f"scan-{index}",
            datetime.now(timezone.utc) - timedelta(minutes=index),
        )

    response = client.get(
        "/discovery/scans?page=2&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["scan_id"] for item in payload["items"]] == ["scan-2", "scan-3"]
    assert payload["total_count"] == 5
    assert payload["page"] == 2
    assert payload["page_size"] == 2
    assert payload["total_pages"] == 3


def test_scan_history_page_size_is_bounded() -> None:
    token = _token("pagination-bounds@example.com")

    assert client.get(
        "/discovery/scans?page=0",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 422
    assert client.get(
        "/discovery/scans?page_size=101",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 422


def test_pagination_count_is_scoped_to_current_user() -> None:
    owner_token = _token("page-owner@example.com")
    other_token = _token("page-other@example.com")
    _seed_scan(_user_id(owner_token), "owner-page-scan")
    _seed_scan(_user_id(other_token), "other-page-scan")

    payload = client.get(
        "/discovery/scans",
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()

    assert payload["total_count"] == 1
    assert [item["scan_id"] for item in payload["items"]] == ["owner-page-scan"]
