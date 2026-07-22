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
from app.models.discovery import EVIDENCE_REVIEW_STATUS_PENDING_REVIEW, DiscoveryScan, EvidenceFinding
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


class ApiFakeTextProvider:
    def get_text(self, document: Document) -> str:
        return "retirement rollover"


def _token(email: str) -> str:
    password = "StrongPass123!"
    assert client.post("/auth/register", json={"email": email, "password": password}).status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def _create_document(token: str) -> str:
    response = client.post(
        "/documents",
        headers={"Authorization": f"Bearer {token}"},
        json={"document_type": "ACCOUNT_STATEMENT", "document_name": "Statement", "mime_type": "text/plain"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_discovery_auth_required() -> None:
    response = client.post("/discovery/scans", json={"document_ids": ["doc-1"]})
    assert response.status_code in (401, 403)


def test_user_can_start_scan(monkeypatch) -> None:
    token = _token("owner@example.com")
    document_id = _create_document(token)
    monkeypatch.setattr(discovery_api.discovery_orchestrator, "text_provider", ApiFakeTextProvider())

    response = client.post("/discovery/scans", headers={"Authorization": f"Bearer {token}"}, json={"document_ids": [document_id]})

    assert response.status_code == 201
    payload = response.json()
    assert set(payload.keys()) == {"scan_id", "status", "created_at"}
    assert payload["status"] == "COMPLETE"
    assert "user_id" not in payload


def test_user_cannot_access_another_users_scan() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    db = SessionLocal()
    try:
        owner_id = client.get("/auth/me", headers={"Authorization": f"Bearer {owner_token}"}).json()["id"]
        scan = DiscoveryScan(id="scan-owner", user_id=owner_id, status="COMPLETE", documents_processed=0, created_at=datetime.now(timezone.utc))
        db.add(scan)
        db.commit()
    finally:
        db.close()

    response = client.get("/discovery/scans/scan-owner", headers={"Authorization": f"Bearer {other_token}"})
    assert response.status_code == 404


def test_findings_endpoint_hides_sensitive_fields() -> None:
    token = _token("owner-findings@example.com")
    user_id = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]
    db = SessionLocal()
    try:
        scan = DiscoveryScan(id="scan-findings", user_id=user_id, status="COMPLETE", documents_processed=1, created_at=datetime.now(timezone.utc))
        finding = EvidenceFinding(
            id="finding-1",
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
    finally:
        db.close()

    response = client.get("/discovery/scans/scan-findings/findings", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    item = response.json()[0]
    assert set(item.keys()) == {"finding_id", "category", "confidence_score", "review_status", "created_at"}
    assert "matched_terms" not in item
    assert "matched_terms_encrypted" not in item
    assert "evidence_excerpt" not in item
    assert "evidence_excerpt_encrypted" not in item


def test_scan_status_response_schema_is_correct() -> None:
    token = _token("status@example.com")
    user_id = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]
    db = SessionLocal()
    try:
        scan = DiscoveryScan(id="scan-status", user_id=user_id, status="RUNNING", documents_processed=2, created_at=datetime.now(timezone.utc))
        db.add(scan)
        db.commit()
    finally:
        db.close()

    response = client.get("/discovery/scans/scan-status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert set(response.json().keys()) == {"scan_id", "status", "documents_processed", "created_at", "completed_at"}