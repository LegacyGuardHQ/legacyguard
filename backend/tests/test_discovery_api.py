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
from app.services.audit import log_event
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
    payload = response.json()
    assert payload["total_count"] == 1
    item = payload["items"][0]
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
    payload = response.json()
    assert set(payload.keys()) == {
        "scan_id",
        "status",
        "documents_processed",
        "created_at",
        "completed_at",
        "lifecycle_state",
        "recovered_from_stale",
        "recovered_at",
        "processing_outcome",
        "processing_outcome_message",
        "background_job_state",
        "background_job_message",
        "retry_count",
        "failure_count",
        "last_failure_at",
    }
    assert payload["lifecycle_state"] == "RUNNING"
    assert payload["processing_outcome"] == "IN_PROGRESS"
    assert payload["processing_outcome_message"] == "Processing is active"
    assert payload["background_job_state"] == "RUNNING"
    assert payload["background_job_message"] == "Background processing is active"
    assert payload["retry_count"] == 0
    assert payload["failure_count"] == 0
    assert payload["last_failure_at"] is None
    assert payload["recovered_from_stale"] is False
    assert payload["recovered_at"] is None
    assert "matched_terms" not in payload
    assert "evidence_excerpt" not in payload
    assert "storage_path" not in payload


def test_scan_status_response_surfaces_recovery_metadata_from_controlled_audit_event() -> None:
    token = _token("status-recovery@example.com")
    user_id = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]
    db = SessionLocal()
    try:
        scan = DiscoveryScan(
            id="scan-recovery",
            user_id=user_id,
            status="COMPLETE",
            documents_processed=1,
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(scan)
        db.commit()
        log_event(
            db,
            user_id=user_id,
            event_type="discovery_started",
            details="Discovery scan recovered from stale running state",
            metadata={
                "scan_id": scan.id,
                "old_status": "RUNNING",
                "new_status": "PENDING",
            },
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/discovery/scans/scan-recovery", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["lifecycle_state"] == "COMPLETED"
    assert payload["recovered_from_stale"] is True
    assert payload["recovered_at"] is not None
    assert payload["status"] == "COMPLETE"
    assert payload["processing_outcome"] == "RECOVERED_AND_COMPLETED"
    assert payload["processing_outcome_message"] == "Recovered and completed"
    assert payload["background_job_state"] == "COMPLETED"
    assert payload["background_job_message"] == "Background processing completed"
    assert payload["retry_count"] == 1
    assert payload["failure_count"] == 0
    assert payload["last_failure_at"] is None


def test_scan_status_response_surfaces_failure_counts_for_background_monitoring() -> None:
    token = _token("status-failure@example.com")
    user_id = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]
    db = SessionLocal()
    try:
        scan = DiscoveryScan(
            id="scan-failure-monitoring",
            user_id=user_id,
            status="FAILED",
            documents_processed=0,
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(scan)
        db.commit()
        log_event(
            db,
            user_id=user_id,
            event_type="discovery_failed",
            details="Discovery scan failed",
            metadata={
                "scan_id": scan.id,
                "old_status": "RUNNING",
                "new_status": "FAILED",
            },
        )
        log_event(
            db,
            user_id=user_id,
            event_type="discovery_failed",
            details="Discovery scan failed",
            metadata={
                "scan_id": scan.id,
                "old_status": "RUNNING",
                "new_status": "FAILED",
            },
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/discovery/scans/scan-failure-monitoring", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILED"
    assert payload["background_job_state"] == "FAILED"
    assert payload["background_job_message"] == "Background processing failed"
    assert payload["retry_count"] == 0
    assert payload["failure_count"] == 2
    assert payload["last_failure_at"] is not None


def test_safe_report_endpoint_returns_only_summary_fields() -> None:
    token = _token("report-owner@example.com")
    user_id = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]
    db = SessionLocal()
    try:
        scan = DiscoveryScan(
            id="scan-report",
            user_id=user_id,
            status="COMPLETE",
            documents_processed=1,
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        finding = EvidenceFinding(
            id="finding-report",
            scan_id=scan.id,
            document_id="doc-report",
            category="RETIREMENT_INDICATOR",
            confidence_score=90,
            review_status=EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
        )
        finding.set_matched_terms('["private-term"]')
        finding.set_evidence_excerpt("Highly sensitive evidence")
        db.add_all([scan, finding])
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/discovery/scans/scan-report/report",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "scan_id",
        "status",
        "documents_processed",
        "total_findings",
        "categories",
        "review_statuses",
        "created_at",
        "completed_at",
    }
    assert payload["documents_processed"] == 1
    assert payload["total_findings"] == 1
    assert payload["categories"] == {"RETIREMENT_INDICATOR": 1}
    assert "private-term" not in str(payload)
    assert "Highly sensitive evidence" not in str(payload)
    assert "document_id" not in payload


def test_safe_report_endpoint_enforces_scan_ownership() -> None:
    owner_token = _token("report-owner-two@example.com")
    other_token = _token("report-other@example.com")
    owner_id = client.get("/auth/me", headers={"Authorization": f"Bearer {owner_token}"}).json()["id"]
    db = SessionLocal()
    try:
        db.add(
            DiscoveryScan(
                id="scan-private-report",
                user_id=owner_id,
                status="COMPLETE",
                documents_processed=0,
                created_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/discovery/scans/scan-private-report/report",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404
