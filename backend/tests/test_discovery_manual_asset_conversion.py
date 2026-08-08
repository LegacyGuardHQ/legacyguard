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
from app.models.asset import ASSET_VERIFICATION_NEEDS_REVIEW, Asset
from app.models.audit_log import AuditLog
from app.models.discovery_asset_link import DiscoveryFindingAssetLink
from app.models.discovery import (
    EVIDENCE_REVIEW_STATUS_CONFIRMED,
    EVIDENCE_REVIEW_STATUS_DISMISSED,
    EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
    DiscoveryScan,
    EvidenceFinding,
)
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


def _create_finding(user_id: str, *, finding_id: str, review_status: str) -> str:
    db = SessionLocal()
    try:
        scan = DiscoveryScan(
            id=f"scan-{finding_id}",
            user_id=user_id,
            status="COMPLETE",
            documents_processed=1,
            created_at=datetime.now(timezone.utc),
        )
        finding = EvidenceFinding(
            id=finding_id,
            scan_id=scan.id,
            document_id=f"doc-{finding_id}",
            category="RETIREMENT_INDICATOR",
            confidence_score=88,
            review_status=review_status,
        )
        finding.set_matched_terms('["401(k)", "account 9876"]')
        finding.set_evidence_excerpt("Sensitive retirement evidence excerpt")
        db.add_all([scan, finding])
        db.commit()
        return finding.id
    finally:
        db.close()


def _payload() -> dict:
    return {
        "asset_name": "Possible former employer retirement account",
        "asset_category": "Retirement",
        "institution": "Example Plan Administrator",
        "description": "Manually entered follow-up record",
        "ownership_type": "Unknown",
        "details": {
            "notes": "Call the plan administrator to verify ownership",
        },
    }


def test_confirmed_finding_can_be_manually_converted_to_unverified_asset() -> None:
    token = _token("convert@example.com")
    user_id = _user_id(token)
    finding_id = _create_finding(
        user_id,
        finding_id="finding-convert",
        review_status=EVIDENCE_REVIEW_STATUS_CONFIRMED,
    )

    response = client.post(
        f"/discovery/findings/{finding_id}/assets",
        headers={"Authorization": f"Bearer {token}"},
        json=_payload(),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["asset_name"] == "Possible former employer retirement account"
    assert payload["is_verified"] is False
    assert payload["verification_status"] == ASSET_VERIFICATION_NEEDS_REVIEW
    assert payload["details"]["notes"] == "Call the plan administrator to verify ownership"
    assert payload["source_context"] == "manual_conversion_from_confirmed_finding"

    db = SessionLocal()
    try:
        asset = db.query(Asset).one()
        assert asset.user_id == user_id
        link = db.query(DiscoveryFindingAssetLink).one()
        assert link.finding_id == finding_id
        assert link.asset_id == asset.id
        assert link.user_id == user_id
        assert link.source_context == "manual_conversion_from_confirmed_finding"
        assert asset.is_verified is False
        assert asset.verification_status == ASSET_VERIFICATION_NEEDS_REVIEW
        assert asset.details.notes_encrypted != "Call the plan administrator to verify ownership"
    finally:
        db.close()


@pytest.mark.parametrize(
    "review_status",
    [EVIDENCE_REVIEW_STATUS_PENDING_REVIEW, EVIDENCE_REVIEW_STATUS_DISMISSED],
)
def test_only_confirmed_finding_can_be_converted(review_status: str) -> None:
    token = _token(f"blocked-{review_status.lower()}@example.com")
    finding_id = _create_finding(
        _user_id(token),
        finding_id=f"finding-{review_status.lower()}",
        review_status=review_status,
    )

    response = client.post(
        f"/discovery/findings/{finding_id}/assets",
        headers={"Authorization": f"Bearer {token}"},
        json=_payload(),
    )

    assert response.status_code == 409
    db = SessionLocal()
    try:
        assert db.query(Asset).count() == 0
    finally:
        db.close()


def test_user_cannot_convert_another_users_finding() -> None:
    owner_token = _token("conversion-owner@example.com")
    other_token = _token("conversion-other@example.com")
    finding_id = _create_finding(
        _user_id(owner_token),
        finding_id="finding-cross-user",
        review_status=EVIDENCE_REVIEW_STATUS_CONFIRMED,
    )

    response = client.post(
        f"/discovery/findings/{finding_id}/assets",
        headers={"Authorization": f"Bearer {other_token}"},
        json=_payload(),
    )

    assert response.status_code == 404


def test_same_finding_cannot_create_multiple_assets() -> None:
    token = _token("conversion-duplicate@example.com")
    finding_id = _create_finding(
        _user_id(token),
        finding_id="finding-duplicate",
        review_status=EVIDENCE_REVIEW_STATUS_CONFIRMED,
    )
    headers = {"Authorization": f"Bearer {token}"}

    assert client.post(
        f"/discovery/findings/{finding_id}/assets",
        headers=headers,
        json=_payload(),
    ).status_code == 201

    second = client.post(
        f"/discovery/findings/{finding_id}/assets",
        headers=headers,
        json=_payload(),
    )
    assert second.status_code == 409

    db = SessionLocal()
    try:
        assert db.query(Asset).count() == 1
    finally:
        db.close()


def test_conversion_does_not_copy_sensitive_finding_evidence() -> None:
    token = _token("conversion-privacy@example.com")
    finding_id = _create_finding(
        _user_id(token),
        finding_id="finding-private-conversion",
        review_status=EVIDENCE_REVIEW_STATUS_CONFIRMED,
    )

    response = client.post(
        f"/discovery/findings/{finding_id}/assets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "asset_name": "Retirement follow-up",
            "asset_category": "Retirement",
        },
    )

    assert response.status_code == 201
    serialized = str(response.json())
    assert "Sensitive retirement evidence excerpt" not in serialized
    assert "account 9876" not in serialized
    assert "matched_terms" not in serialized
    assert "evidence_excerpt" not in serialized

    db = SessionLocal()
    try:
        asset = db.query(Asset).one()
        assert "Sensitive retirement evidence excerpt" not in str(asset.description)
        assert "account 9876" not in str(asset.description)
    finally:
        db.close()


def test_conversion_audit_event_contains_only_safe_identifiers() -> None:
    token = _token("conversion-audit@example.com")
    finding_id = _create_finding(
        _user_id(token),
        finding_id="finding-audit-conversion",
        review_status=EVIDENCE_REVIEW_STATUS_CONFIRMED,
    )

    response = client.post(
        f"/discovery/findings/{finding_id}/assets",
        headers={"Authorization": f"Bearer {token}"},
        json=_payload(),
    )
    assert response.status_code == 201
    asset_id = response.json()["id"]

    db = SessionLocal()
    try:
        audit = db.query(AuditLog).filter(AuditLog.event_type == "asset_created_from_finding").one()
        assert audit.event_metadata == {
            "resource_type": "asset",
            "resource_id": asset_id,
            "asset_id": asset_id,
            "finding_id": finding_id,
            "event_type": "asset_created_from_finding",
        }
        audit_text = f"{audit.details} {audit.event_metadata}"
        assert "Sensitive retirement evidence excerpt" not in audit_text
        assert "account 9876" not in audit_text
    finally:
        db.close()


def test_conversion_payload_cannot_claim_asset_is_verified() -> None:
    token = _token("conversion-validation@example.com")
    finding_id = _create_finding(
        _user_id(token),
        finding_id="finding-validation-conversion",
        review_status=EVIDENCE_REVIEW_STATUS_CONFIRMED,
    )
    payload = _payload()
    payload["is_verified"] = True
    payload["verification_status"] = "VERIFIED"

    response = client.post(
        f"/discovery/findings/{finding_id}/assets",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 422


def test_conversion_and_audit_roll_back_together_on_precommit_failure(monkeypatch) -> None:
    token = _token("conversion-rollback@example.com")
    finding_id = _create_finding(
        _user_id(token),
        finding_id="finding-conversion-rollback",
        review_status=EVIDENCE_REVIEW_STATUS_CONFIRMED,
    )

    def fail_after_audit_flush(*args, **kwargs):
        add_audit_event(*args, **kwargs)
        raise RuntimeError("simulated precommit failure")

    monkeypatch.setattr(discovery_api, "log_event", fail_after_audit_flush)

    with pytest.raises(RuntimeError, match="simulated precommit failure"):
        client.post(
            f"/discovery/findings/{finding_id}/assets",
            headers={"Authorization": f"Bearer {token}"},
            json=_payload(),
        )

    db = SessionLocal()
    try:
        assert db.query(Asset).count() == 0
        assert db.query(DiscoveryFindingAssetLink).count() == 0
        assert db.query(AuditLog).filter(AuditLog.event_type == "asset_created_from_finding").count() == 0
    finally:
        db.close()
