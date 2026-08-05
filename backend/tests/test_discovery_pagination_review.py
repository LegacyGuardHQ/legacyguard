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
from app.models.discovery import (
    EVIDENCE_REVIEW_STATUS_CONFIRMED,
    EVIDENCE_REVIEW_STATUS_DISMISSED,
    EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
    DiscoveryScan,
    EvidenceFinding,
)
from app.models.document import Document
from app.services.discovery_categories import (
    INSURANCE_INDICATOR,
    RETIREMENT_INDICATOR,
)
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


def _seed_scan_with_findings(
    user_id: str,
    scan_id: str,
    statuses: list[str],
    categories: list[str] | None = None,
) -> None:
    if categories is not None:
        assert len(categories) == len(statuses)

    db = SessionLocal()
    try:
        db.add(
            DiscoveryScan(
                id=scan_id,
                user_id=user_id,
                status="COMPLETE",
                documents_processed=len(statuses),
                created_at=datetime.now(timezone.utc),
            )
        )
        for index, review_status in enumerate(statuses):
            document_id = f"{scan_id}-doc-{index}"
            db.add(
                Document(
                    id=document_id,
                    user_id=user_id,
                    document_type="ACCOUNT_STATEMENT",
                    document_name=f"Document {index}",
                    mime_type="text/plain",
                )
            )
            finding = EvidenceFinding(
                id=f"{scan_id}-finding-{index}",
                scan_id=scan_id,
                document_id=document_id,
                category=(
                    categories[index]
                    if categories is not None
                    else RETIREMENT_INDICATOR if index % 2 == 0 else INSURANCE_INDICATOR
                ),
                confidence_score=80 + index,
                review_status=review_status,
                created_at=datetime.now(timezone.utc) + timedelta(seconds=index),
            )
            finding.set_matched_terms('["private-term"]')
            finding.set_evidence_excerpt("Sensitive evidence")
            db.add(finding)
        db.commit()
    finally:
        db.close()


def test_scan_findings_are_paginated_with_consistent_metadata() -> None:
    token = _token("finding-pages@example.com")
    _seed_scan_with_findings(_user_id(token), "scan-pages", [EVIDENCE_REVIEW_STATUS_PENDING_REVIEW] * 5)

    response = client.get(
        "/discovery/scans/scan-pages/findings?page=2&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["finding_id"] for item in payload["items"]] == ["scan-pages-finding-2", "scan-pages-finding-3"]
    assert payload == {
        "items": payload["items"],
        "total_count": 5,
        "page": 2,
        "page_size": 2,
        "total_pages": 3,
    }


def test_scan_findings_support_review_status_filter_before_pagination() -> None:
    token = _token("finding-filter@example.com")
    _seed_scan_with_findings(
        _user_id(token),
        "scan-filter",
        [
            EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
            EVIDENCE_REVIEW_STATUS_CONFIRMED,
            EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
            EVIDENCE_REVIEW_STATUS_DISMISSED,
        ],
    )

    response = client.get(
        f"/discovery/scans/scan-filter/findings?review_status={EVIDENCE_REVIEW_STATUS_PENDING_REVIEW}&page_size=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 2
    assert payload["total_pages"] == 2
    assert len(payload["items"]) == 1
    assert payload["items"][0]["review_status"] == EVIDENCE_REVIEW_STATUS_PENDING_REVIEW


def test_scan_findings_reject_invalid_pagination_and_status() -> None:
    token = _token("finding-invalid@example.com")
    _seed_scan_with_findings(_user_id(token), "scan-invalid", [EVIDENCE_REVIEW_STATUS_PENDING_REVIEW])
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/discovery/scans/scan-invalid/findings?page=0", headers=headers).status_code == 422
    assert client.get("/discovery/scans/scan-invalid/findings?page_size=101", headers=headers).status_code == 422
    assert client.get("/discovery/scans/scan-invalid/findings?review_status=UNKNOWN", headers=headers).status_code == 422


def test_scan_findings_empty_page_is_safe_and_consistent() -> None:
    token = _token("finding-empty-page@example.com")
    _seed_scan_with_findings(_user_id(token), "scan-empty-page", [EVIDENCE_REVIEW_STATUS_PENDING_REVIEW])

    response = client.get(
        "/discovery/scans/scan-empty-page/findings?page=9&page_size=20",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total_count": 1,
        "page": 9,
        "page_size": 20,
        "total_pages": 1,
    }


def test_review_queue_defaults_to_pending_and_is_paginated() -> None:
    token = _token("review-queue@example.com")
    user_id = _user_id(token)
    _seed_scan_with_findings(
        user_id,
        "queue-scan-a",
        [EVIDENCE_REVIEW_STATUS_PENDING_REVIEW, EVIDENCE_REVIEW_STATUS_CONFIRMED],
    )
    _seed_scan_with_findings(
        user_id,
        "queue-scan-b",
        [EVIDENCE_REVIEW_STATUS_PENDING_REVIEW, EVIDENCE_REVIEW_STATUS_PENDING_REVIEW],
    )

    response = client.get(
        "/discovery/findings/review-queue?page=2&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 3
    assert payload["total_pages"] == 2
    assert len(payload["items"]) == 1
    assert all(item["review_status"] == EVIDENCE_REVIEW_STATUS_PENDING_REVIEW for item in payload["items"])


def test_review_queue_filters_category_and_status_before_pagination() -> None:
    token = _token("review-queue-category@example.com")
    user_id = _user_id(token)
    _seed_scan_with_findings(
        user_id,
        "category-queue",
        [
            EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
            EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
            EVIDENCE_REVIEW_STATUS_CONFIRMED,
            EVIDENCE_REVIEW_STATUS_PENDING_REVIEW,
        ],
        [
            RETIREMENT_INDICATOR,
            INSURANCE_INDICATOR,
            RETIREMENT_INDICATOR,
            RETIREMENT_INDICATOR,
        ],
    )

    response = client.get(
        "/discovery/findings/review-queue"
        f"?review_status={EVIDENCE_REVIEW_STATUS_PENDING_REVIEW}"
        f"&category={RETIREMENT_INDICATOR}&page=2&page_size=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 2
    assert payload["total_pages"] == 2
    assert payload["page"] == 2
    assert len(payload["items"]) == 1
    assert payload["items"][0]["category"] == RETIREMENT_INDICATOR
    assert payload["items"][0]["review_status"] == EVIDENCE_REVIEW_STATUS_PENDING_REVIEW


def test_review_queue_category_filter_is_owner_scoped_and_privacy_safe() -> None:
    owner_token = _token("category-owner@example.com")
    other_token = _token("category-other@example.com")
    _seed_scan_with_findings(
        _user_id(owner_token),
        "category-owner",
        [EVIDENCE_REVIEW_STATUS_PENDING_REVIEW],
        [INSURANCE_INDICATOR],
    )
    _seed_scan_with_findings(
        _user_id(other_token),
        "category-other",
        [EVIDENCE_REVIEW_STATUS_PENDING_REVIEW] * 2,
        [INSURANCE_INDICATOR, INSURANCE_INDICATOR],
    )

    response = client.get(
        f"/discovery/findings/review-queue?category={INSURANCE_INDICATOR}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 1
    assert [item["finding_id"] for item in payload["items"]] == ["category-owner-finding-0"]
    assert set(payload["items"][0]) == {
        "finding_id",
        "category",
        "confidence_score",
        "review_status",
        "created_at",
    }
    assert "private-term" not in str(payload)
    assert "Sensitive evidence" not in str(payload)


def test_review_queue_category_filter_supports_empty_results() -> None:
    token = _token("category-empty@example.com")
    _seed_scan_with_findings(
        _user_id(token),
        "category-empty",
        [EVIDENCE_REVIEW_STATUS_PENDING_REVIEW],
        [RETIREMENT_INDICATOR],
    )

    response = client.get(
        f"/discovery/findings/review-queue?category={INSURANCE_INDICATOR}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total_count": 0,
        "page": 1,
        "page_size": 20,
        "total_pages": 0,
    }


def test_review_queue_ownership_filter_applies_before_count_and_pagination() -> None:
    owner_token = _token("queue-owner@example.com")
    other_token = _token("queue-other@example.com")
    _seed_scan_with_findings(_user_id(owner_token), "owner-queue", [EVIDENCE_REVIEW_STATUS_PENDING_REVIEW])
    _seed_scan_with_findings(_user_id(other_token), "other-queue", [EVIDENCE_REVIEW_STATUS_PENDING_REVIEW] * 3)

    payload = client.get(
        "/discovery/findings/review-queue",
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()

    assert payload["total_count"] == 1
    assert [item["finding_id"] for item in payload["items"]] == ["owner-queue-finding-0"]


def test_review_queue_can_show_confirmed_without_exposing_sensitive_fields() -> None:
    token = _token("queue-confirmed@example.com")
    _seed_scan_with_findings(_user_id(token), "confirmed-queue", [EVIDENCE_REVIEW_STATUS_CONFIRMED])

    response = client.get(
        f"/discovery/findings/review-queue?review_status={EVIDENCE_REVIEW_STATUS_CONFIRMED}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 1
    item = payload["items"][0]
    assert set(item) == {"finding_id", "category", "confidence_score", "review_status", "created_at"}
    assert "private-term" not in str(payload)
    assert "Sensitive evidence" not in str(payload)


def test_review_queue_rejects_invalid_parameters() -> None:
    token = _token("queue-invalid@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/discovery/findings/review-queue?page=0", headers=headers).status_code == 422
    assert client.get("/discovery/findings/review-queue?page_size=101", headers=headers).status_code == 422
    assert client.get("/discovery/findings/review-queue?review_status=UNKNOWN", headers=headers).status_code == 422
    assert client.get("/discovery/findings/review-queue?category=UNKNOWN", headers=headers).status_code == 422


def test_review_queue_requires_authentication_with_category_filter() -> None:
    response = client.get(f"/discovery/findings/review-queue?category={RETIREMENT_INDICATOR}")

    assert response.status_code == 401


def test_reopened_finding_returns_to_default_review_queue() -> None:
    token = _token("queue-reopened@example.com")
    user_id = _user_id(token)
    _seed_scan_with_findings(user_id, "queue-reopened", [EVIDENCE_REVIEW_STATUS_CONFIRMED])
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(
        "/discovery/findings/queue-reopened-finding-0",
        headers=headers,
        json={"review_status": EVIDENCE_REVIEW_STATUS_PENDING_REVIEW},
    )
    assert response.status_code == 200

    queue = client.get("/discovery/findings/review-queue", headers=headers)
    assert queue.status_code == 200
    assert queue.json()["total_count"] == 1
    assert queue.json()["items"][0]["finding_id"] == "queue-reopened-finding-0"
