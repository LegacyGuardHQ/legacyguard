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
from app.models.discovery import (
    DISCOVERY_SCAN_STATUS_COMPLETE,
    DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS,
    DISCOVERY_SCAN_STATUS_FAILED,
    DISCOVERY_SCAN_STATUS_PENDING,
    DISCOVERY_SCAN_STATUS_RUNNING,
    EVIDENCE_REVIEW_STATUS_CONFIRMED,
    EVIDENCE_REVIEW_STATUS_DISMISSED,
    EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
    DiscoveryScan,
    EvidenceFinding,
)
from app.models.discovery_scan_document import (
    DISCOVERY_DOCUMENT_STATUS_COMPLETED,
    DISCOVERY_DOCUMENT_STATUS_FAILED,
    DISCOVERY_DOCUMENT_STATUS_PENDING,
    DISCOVERY_DOCUMENT_STATUS_PROCESSING,
    DISCOVERY_DOCUMENT_STATUS_SKIPPED,
    DISCOVERY_DOCUMENT_WARNING_EMPTY_DOCUMENT,
    DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED,
    DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION,
    DiscoveryScanDocument,
)
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
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _user_id(token: str) -> str:
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_empty_dashboard_returns_complete_zero_filled_contract() -> None:
    token = _token("empty-dashboard@example.com")

    response = client.get("/discovery/dashboard", headers=_headers(token))

    assert response.status_code == 200
    assert response.json() == {
        "total_scans": 0,
        "scans_by_status": {
            "PENDING": 0,
            "RUNNING": 0,
            "COMPLETE": 0,
            "COMPLETED_WITH_WARNINGS": 0,
            "FAILED": 0,
        },
        "total_findings": 0,
        "pending_reviews": 0,
        "findings_by_category": {},
        "findings_by_review_status": {
            "PENDING_REVIEW": 0,
            "CONFIRMED": 0,
            "DISMISSED": 0,
        },
        "recent_scans": [],
    }


def test_empty_owned_scan_returns_empty_document_collection() -> None:
    token = _token("empty-scan@example.com")
    user_id = _user_id(token)
    db = SessionLocal()
    try:
        db.add(DiscoveryScan(id="empty-scan", user_id=user_id, status=DISCOVERY_SCAN_STATUS_PENDING))
        db.commit()
    finally:
        db.close()

    response = client.get("/discovery/scans/empty-scan/documents", headers=_headers(token))

    assert response.status_code == 200
    assert response.json() == []


def test_dashboard_is_owner_scoped_and_aggregates_every_status_deterministically() -> None:
    owner_token = _token("dashboard-owner@example.com")
    other_token = _token("dashboard-other@example.com")
    owner_id = _user_id(owner_token)
    other_id = _user_id(other_token)
    tied_created_at = datetime.now(timezone.utc)
    owner_scans = [
        ("owner-scan-a", DISCOVERY_SCAN_STATUS_PENDING),
        ("owner-scan-b", DISCOVERY_SCAN_STATUS_RUNNING),
        ("owner-scan-c", DISCOVERY_SCAN_STATUS_COMPLETE),
        ("owner-scan-d", DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS),
        ("owner-scan-e", DISCOVERY_SCAN_STATUS_FAILED),
        ("owner-scan-f", DISCOVERY_SCAN_STATUS_COMPLETE),
    ]
    finding_specs = [
        ("RETIREMENT_INDICATOR", EVIDENCE_REVIEW_STATUS_PENDING_REVIEW),
        ("RETIREMENT_INDICATOR", EVIDENCE_REVIEW_STATUS_PENDING_REVIEW),
        ("INSURANCE_INDICATOR", EVIDENCE_REVIEW_STATUS_CONFIRMED),
        ("EMPLOYER_BENEFIT_INDICATOR", EVIDENCE_REVIEW_STATUS_DISMISSED),
    ]
    db = SessionLocal()
    try:
        for index, (scan_id, scan_status) in enumerate(owner_scans):
            db.add(
                DiscoveryScan(
                    id=scan_id,
                    user_id=owner_id,
                    status=scan_status,
                    documents_processed=index,
                    created_at=tied_created_at,
                )
            )
        db.flush()

        for index, (category, review_status) in enumerate(finding_specs):
            document = Document(
                id=f"owner-finding-document-{index}",
                user_id=owner_id,
                document_type="ACCOUNT_STATEMENT",
                document_name=f"Owner source {index}",
                original_filename=f"private-owner-{index}.pdf",
                checksum_sha256=f"private-checksum-{index}",
            )
            finding = EvidenceFinding(
                id=f"owner-finding-{index}",
                scan_id=owner_scans[index][0],
                document_id=document.id,
                category=category,
                confidence_score=80,
                review_status=review_status,
            )
            finding.set_matched_terms('["private matched term"]')
            finding.set_evidence_excerpt("private evidence excerpt")
            db.add(document)
            db.flush()
            db.add(finding)

        other_scan = DiscoveryScan(
            id="other-scan-z",
            user_id=other_id,
            status=DISCOVERY_SCAN_STATUS_FAILED,
            documents_processed=1,
            created_at=tied_created_at,
        )
        other_document = Document(
            id="other-document",
            user_id=other_id,
            document_type="TAX_DOCUMENT",
            document_name="Other private document",
        )
        db.add_all([other_scan, other_document])
        db.flush()
        db.add(
            EvidenceFinding(
                    id="other-finding",
                    scan_id=other_scan.id,
                    document_id=other_document.id,
                    category="OTHER_PRIVATE_CATEGORY",
                    confidence_score=99,
                    review_status=EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/discovery/dashboard", headers=_headers(owner_token))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_scans"] == 6
    assert payload["scans_by_status"] == {
        "PENDING": 1,
        "RUNNING": 1,
        "COMPLETE": 2,
        "COMPLETED_WITH_WARNINGS": 1,
        "FAILED": 1,
    }
    assert payload["total_findings"] == 4
    assert payload["pending_reviews"] == 2
    assert payload["findings_by_category"] == {
        "EMPLOYER_BENEFIT_INDICATOR": 1,
        "INSURANCE_INDICATOR": 1,
        "RETIREMENT_INDICATOR": 2,
    }
    assert payload["findings_by_review_status"] == {
        "PENDING_REVIEW": 2,
        "CONFIRMED": 1,
        "DISMISSED": 1,
    }
    assert [scan["scan_id"] for scan in payload["recent_scans"]] == [
        "owner-scan-f",
        "owner-scan-e",
        "owner-scan-d",
        "owner-scan-c",
        "owner-scan-b",
    ]
    serialized = str(payload).lower()
    for prohibited in ("other", "excerpt", "matched", "filename", "checksum", "storage", "content"):
        assert prohibited not in serialized

    other_response = client.get("/discovery/dashboard", headers=_headers(other_token))
    assert other_response.status_code == 200
    assert other_response.json()["total_scans"] == 1
    assert other_response.json()["total_findings"] == 1


def test_scan_documents_serialize_all_states_warnings_and_tied_order_safely() -> None:
    owner_token = _token("scan-doc-owner@example.com")
    other_token = _token("scan-doc-other@example.com")
    owner_id = _user_id(owner_token)
    tied_created_at = datetime.now(timezone.utc)
    tracking_specs = [
        ("a", DISCOVERY_DOCUMENT_STATUS_PENDING, None),
        ("b", DISCOVERY_DOCUMENT_STATUS_PROCESSING, None),
        ("c", DISCOVERY_DOCUMENT_STATUS_COMPLETED, None),
        ("d", DISCOVERY_DOCUMENT_STATUS_FAILED, DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED),
        ("e", DISCOVERY_DOCUMENT_STATUS_SKIPPED, DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION),
        ("f", DISCOVERY_DOCUMENT_STATUS_COMPLETED, DISCOVERY_DOCUMENT_WARNING_EMPTY_DOCUMENT),
    ]
    db = SessionLocal()
    try:
        scan = DiscoveryScan(
            id="scan-documents",
            user_id=owner_id,
            status=DISCOVERY_SCAN_STATUS_COMPLETE,
            created_at=tied_created_at,
        )
        db.add(scan)
        db.flush()
        for suffix, processing_status, warning_code in tracking_specs:
            document = Document(
                id=f"safe-document-{suffix}",
                user_id=owner_id,
                document_type="RETIREMENT_DOCUMENT",
                document_name=f"Safe document {suffix.upper()}",
                original_filename=f"private-account-{suffix}.pdf",
                checksum_sha256=f"private-checksum-{suffix}",
            )
            document.set_description(f"private description {suffix}")
            document.set_storage_reference(f"private/storage/{suffix}")
            document.set_encryption_key_reference(f"private-key-{suffix}")
            tracking = DiscoveryScanDocument(
                id=f"tracking-{suffix}",
                scan_id=scan.id,
                document_id=document.id,
                status=processing_status,
                warning_code=warning_code,
                created_at=tied_created_at,
            )
            db.add(document)
            db.flush()
            db.add(tracking)
        db.commit()
    finally:
        db.close()

    response = client.get("/discovery/scans/scan-documents/documents", headers=_headers(owner_token))

    assert response.status_code == 200
    payload = response.json()
    assert [
        {key: value for key, value in item.items() if key != "created_at"}
        for item in payload
    ] == [
        {
            "document_id": f"safe-document-{suffix}",
            "document_name": f"Safe document {suffix.upper()}",
            "document_type": "RETIREMENT_DOCUMENT",
            "status": processing_status,
            "warning_code": warning_code,
        }
        for suffix, processing_status, warning_code in tracking_specs
    ]
    for item in payload:
        created_at = datetime.fromisoformat(item["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        assert created_at == tied_created_at
    serialized = str(payload).lower()
    for prohibited in (
        "private-account",
        "private-checksum",
        "private description",
        "private/storage",
        "private-key",
        "filename",
        "checksum",
        "storage_reference",
        "key_reference",
        "document_content",
        "extracted_text",
    ):
        assert prohibited not in serialized
    assert client.get(
        "/discovery/scans/scan-documents/documents", headers=_headers(other_token)
    ).status_code == 404


def test_finding_detail_is_owner_scoped_and_excludes_sensitive_evidence() -> None:
    owner_token = _token("finding-detail-owner@example.com")
    other_token = _token("finding-detail-other@example.com")
    owner_id = _user_id(owner_token)
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        scan = DiscoveryScan(
            id="finding-scan",
            user_id=owner_id,
            status=DISCOVERY_SCAN_STATUS_COMPLETE,
            created_at=now,
        )
        document = Document(
            id="finding-document",
            user_id=owner_id,
            document_type="EMPLOYER_BENEFIT_DOCUMENT",
            document_name="Benefits summary",
            original_filename="private-benefits.pdf",
            checksum_sha256="private-checksum",
        )
        document.set_storage_reference("private/storage/reference")
        document.set_encryption_key_reference("private-key-reference")
        finding = EvidenceFinding(
            id="finding-detail",
            scan_id=scan.id,
            document_id=document.id,
            category="RETIREMENT_INDICATOR",
            confidence_score=87,
            review_status=EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
            created_at=now,
        )
        finding.set_matched_terms('["private employer"]')
        finding.set_evidence_excerpt("private account evidence")
        db.add_all([scan, document])
        db.flush()
        db.add(finding)
        db.commit()
    finally:
        db.close()

    response = client.get("/discovery/findings/finding-detail", headers=_headers(owner_token))

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "finding_id",
        "scan_id",
        "document_id",
        "document_name",
        "document_type",
        "category",
        "confidence_score",
        "review_status",
        "created_at",
    }
    assert payload["document_name"] == "Benefits summary"
    serialized = str(payload).lower()
    for prohibited in (
        "private",
        "evidence_excerpt",
        "matched_terms",
        "filename",
        "checksum",
        "storage_reference",
        "key_reference",
        "document_content",
        "extracted_text",
    ):
        assert prohibited not in serialized
    assert client.get(
        "/discovery/findings/finding-detail", headers=_headers(other_token)
    ).status_code == 404


def test_openapi_describes_processing_warnings_and_confidence_meaning() -> None:
    schemas = app.openapi()["components"]["schemas"]
    document_properties = schemas["DiscoveryScanDocumentResponse"]["properties"]
    finding_properties = schemas["EvidenceFindingDetailResponse"]["properties"]

    status_description = document_properties["status"]["description"]
    for state in ("PENDING", "PROCESSING", "COMPLETED", "FAILED", "SKIPPED"):
        assert state in status_description

    warning_description = document_properties["warning_code"]["description"]
    assert "PROCESSING_FAILED" in warning_description
    assert "UNSUPPORTED_EXTRACTION" in warning_description
    assert "not fully processed" in warning_description

    confidence_description = finding_properties["confidence_score"]["description"]
    assert "Rule-based" in confidence_description
    assert "not a probability" in confidence_description
    assert "ownership determination" in confidence_description
    assert "financial verification" in confidence_description


@pytest.mark.parametrize(
    "path",
    [
        "/discovery/dashboard",
        "/discovery/scans/unknown/documents",
        "/discovery/findings/unknown",
    ],
)
def test_dashboard_contracts_require_authentication(path: str) -> None:
    assert client.get(path).status_code in (401, 403)
