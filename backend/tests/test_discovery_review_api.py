import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.api import discovery as discovery_api
from app.database.connection import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.discovery import EVIDENCE_REVIEW_STATUS_CONFIRMED, EVIDENCE_REVIEW_STATUS_DISMISSED, EVIDENCE_REVIEW_STATUS_PENDING_REVIEW, DiscoveryScan, EvidenceFinding
from app.services.rate_limit import rate_limiter
from app.services.audit import log_event as add_audit_event

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

    response = client.patch(f"/discovery/findings/{finding_id}", headers={"Authorization": f"Bearer {token}"}, json={"review_status": "UNKNOWN"})

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

def test_user_can_reopen_confirmed_finding() -> None:
    token = _token("reopen-confirmed@example.com")
    finding_id = _create_finding(_user_id(token), "finding-reopen-confirmed")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.patch(
        f"/discovery/findings/{finding_id}",
        headers=headers,
        json={"review_status": EVIDENCE_REVIEW_STATUS_CONFIRMED},
    ).status_code == 200

    response = client.patch(
        f"/discovery/findings/{finding_id}",
        headers=headers,
        json={"review_status": EVIDENCE_REVIEW_STATUS_PENDING_REVIEW},
    )

    assert response.status_code == 200
    assert response.json()["review_status"] == EVIDENCE_REVIEW_STATUS_PENDING_REVIEW

    db = SessionLocal()
    try:
        audit = db.query(AuditLog).filter(AuditLog.event_type == "finding_review_reopened").one()
        assert audit.event_metadata["old_status"] == EVIDENCE_REVIEW_STATUS_CONFIRMED
        assert audit.event_metadata["new_status"] == EVIDENCE_REVIEW_STATUS_PENDING_REVIEW
    finally:
        db.close()


def test_user_can_correct_confirmed_finding_to_dismissed() -> None:
    token = _token("correct-review@example.com")
    finding_id = _create_finding(_user_id(token), "finding-correct-review")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.patch(
        f"/discovery/findings/{finding_id}",
        headers=headers,
        json={"review_status": EVIDENCE_REVIEW_STATUS_CONFIRMED},
    ).status_code == 200

    response = client.patch(
        f"/discovery/findings/{finding_id}",
        headers=headers,
        json={"review_status": EVIDENCE_REVIEW_STATUS_DISMISSED},
    )

    assert response.status_code == 200
    assert response.json()["review_status"] == EVIDENCE_REVIEW_STATUS_DISMISSED

    db = SessionLocal()
    try:
        audit = db.query(AuditLog).filter(AuditLog.event_type == "finding_review_corrected").one()
        assert audit.event_metadata["old_status"] == EVIDENCE_REVIEW_STATUS_CONFIRMED
        assert audit.event_metadata["new_status"] == EVIDENCE_REVIEW_STATUS_DISMISSED
    finally:
        db.close()


def test_same_review_status_is_rejected_without_new_audit_event() -> None:
    token = _token("same-review@example.com")
    finding_id = _create_finding(_user_id(token), "finding-same-review")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.patch(
        f"/discovery/findings/{finding_id}",
        headers=headers,
        json={"review_status": EVIDENCE_REVIEW_STATUS_CONFIRMED},
    )
    assert first.status_code == 200

    second = client.patch(
        f"/discovery/findings/{finding_id}",
        headers=headers,
        json={"review_status": EVIDENCE_REVIEW_STATUS_CONFIRMED},
    )
    assert second.status_code == 409

    db = SessionLocal()
    try:
        assert db.query(AuditLog).filter(AuditLog.event_type == "finding_reviewed").count() == 1
    finally:
        db.close()


def test_review_status_changes_do_not_create_assets() -> None:
    from app.models.asset import Asset

    token = _token("no-auto-asset@example.com")
    finding_id = _create_finding(_user_id(token), "finding-no-auto-asset")
    headers = {"Authorization": f"Bearer {token}"}

    for review_status in (
        EVIDENCE_REVIEW_STATUS_CONFIRMED,
        EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
        EVIDENCE_REVIEW_STATUS_DISMISSED,
    ):
        response = client.patch(
            f"/discovery/findings/{finding_id}",
            headers=headers,
            json={"review_status": review_status},
        )
        assert response.status_code == 200

    db = SessionLocal()
    try:
        assert db.query(Asset).count() == 0
    finally:
        db.close()


def test_review_mutation_and_audit_roll_back_together_on_precommit_failure(monkeypatch) -> None:
    token = _token("review-rollback@example.com")
    finding_id = _create_finding(_user_id(token), "finding-review-rollback")

    def fail_after_audit_flush(*args, **kwargs):
        add_audit_event(*args, **kwargs)
        raise RuntimeError("simulated precommit failure")

    monkeypatch.setattr(discovery_api, "log_event", fail_after_audit_flush)

    with pytest.raises(RuntimeError, match="simulated precommit failure"):
        client.patch(
            f"/discovery/findings/{finding_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"review_status": EVIDENCE_REVIEW_STATUS_CONFIRMED},
        )

    db = SessionLocal()
    try:
        finding = db.query(EvidenceFinding).filter(EvidenceFinding.id == finding_id).one()
        assert finding.review_status == EVIDENCE_REVIEW_STATUS_PENDING_REVIEW
        assert db.query(AuditLog).filter(AuditLog.event_type == "finding_reviewed").count() == 0
    finally:
        db.close()
