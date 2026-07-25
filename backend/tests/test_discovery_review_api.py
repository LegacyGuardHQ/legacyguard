import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.database.connection import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.discovery import EVIDENCE_REVIEW_STATUS_CONFIRMED, EVIDENCE_REVIEW_STATUS_DISMISSED, EVIDENCE_REVIEW_STATUS_PENDING_REVIEW, DiscoveryScan, EvidenceFinding
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


def _create_finding(user_id: str, finding_id: str = "finding-1") -> str:
    db = SessionLocal()
    try:
        scan = DiscoveryScan(id=f"scan-{finding_id}", user_id=user_id, status="COMPLETE", documents_processed=1, created_at=datetime.now(timezone.utc))
        finding = EvidenceFinding(
            id=finding_id,
            scan_id=scan.id,
            document_id="doc-1",
            category="RETIREMENT_INDICATOR",
            confidence_score=85,
            review_status=EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
        )
        finding.set_matched_terms('["retirement"]')
        finding.set_evidence_excerpt("Sensitive excerpt")
        db.add(scan)
        db.add(finding)
        db.commit()
        return finding.id
    finally:
        db.close()


def test_user_can_confirm_finding() -> None:
    token = _token("confirm@example.com")
    finding_id = _create_finding(_user_id(token))

    response = client.patch(f"/discovery/findings/{finding_id}", headers={"Authorization": f"Bearer {token}"}, json={"review_status": EVIDENCE_REVIEW_STATUS_CONFIRMED})

    assert response.status_code == 200
    assert response.json()["review_status"] == EVIDENCE_REVIEW_STATUS_CONFIRMED


def test_user_can_dismiss_finding() -> None:
    token = _token("dismiss@example.com")
    finding_id = _create_finding(_user_id(token))

    response = client.patch(f"/discovery/findings/{finding_id}", headers={"Authorization": f"Bearer {token}"}, json={"review_status": EVIDENCE_REVIEW_STATUS_DISMISSED})

    assert response.status_code == 200
    assert response.json()["review_status"] == EVIDENCE_REVIEW_STATUS_DISMISSED


def test_user_cannot_review_another_users_finding() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    finding_id = _create_finding(_user_id(owner_token))

    response = client.patch(f"/discovery/findings/{finding_id}", headers={"Authorization": f"Bearer {other_token}"}, json={"review_status": EVIDENCE_REVIEW_STATUS_CONFIRMED})

    assert response.status_code == 404


def test_invalid_review_status_rejected() -> None:
    token = _token("invalid@example.com")
    finding_id = _create_finding(_user_id(token))

    response = client.patch(f"/discovery/findings/{finding_id}", headers={"Authorization": f"Bearer {token}"}, json={"review_status": "PENDING_REVIEW"})

    assert response.status_code == 422


def test_review_response_hides_sensitive_fields() -> None:
    token = _token("private@example.com")
    finding_id = _create_finding(_user_id(token))

    response = client.patch(f"/discovery/findings/{finding_id}", headers={"Authorization": f"Bearer {token}"}, json={"review_status": EVIDENCE_REVIEW_STATUS_CONFIRMED})
    payload = response.json()

    assert set(payload.keys()) == {"finding_id", "category", "confidence_score", "review_status", "created_at"}
    assert "matched_terms" not in payload
    assert "matched_terms_encrypted" not in payload
    assert "evidence_excerpt" not in payload
    assert "evidence_excerpt_encrypted" not in payload


def test_review_audit_event_generated_without_sensitive_content() -> None:
    token = _token("audit@example.com")
    finding_id = _create_finding(_user_id(token))

    response = client.patch(f"/discovery/findings/{finding_id}", headers={"Authorization": f"Bearer {token}"}, json={"review_status": EVIDENCE_REVIEW_STATUS_CONFIRMED})
    assert response.status_code == 200

    db = SessionLocal()
    try:
        audit = db.query(AuditLog).filter(AuditLog.event_type == "finding_reviewed").one()
        assert audit.details == "Discovery finding review status changed"
        assert audit.event_metadata == {
            "resource_type": "evidence_finding",
            "resource_id": finding_id,
            "finding_id": finding_id,
            "event_type": "finding_reviewed",
            "old_status": "PENDING_REVIEW",
            "new_status": EVIDENCE_REVIEW_STATUS_CONFIRMED,
        }
        assert "Sensitive excerpt" not in audit.details
        assert "retirement" not in audit.details
        assert "Sensitive excerpt" not in str(audit.event_metadata)
        assert "retirement" not in str(audit.event_metadata)
    finally:
        db.close()