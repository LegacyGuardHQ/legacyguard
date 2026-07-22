import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.database.connection import SessionLocal
from app.main import app
from app.models.asset import ASSET_STATUS_ARCHIVED, ASSET_VERIFICATION_VERIFIED, Asset
from app.models.asset_detail import AssetDetail
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
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def _create_asset(token: str, name: str = "Checking Account") -> dict:
    response = client.post(
        "/assets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "asset_name": name,
            "asset_category": "Bank Account",
            "institution": "Example Bank",
            "estimated_value": "2500.00",
            "ownership_type": "Individual",
            "details": {
                "account_number": "123456789",
                "policy_number": "POL-123",
                "notes": "Private asset note",
                "claim_instructions": "Call the bank estate department",
            },
        },
    )
    assert response.status_code == 201
    return response.json()


def test_authenticated_user_creates_asset() -> None:
    token = _token("owner@example.com")

    payload = _create_asset(token)

    assert payload["id"]
    assert payload["asset_name"] == "Checking Account"
    assert payload["details"]["account_number"] == "123456789"
    assert payload["details"]["claim_instructions"] == "Call the bank estate department"
    assert "user_id" not in payload
    assert "created_by" not in payload
    assert "modified_by" not in payload


def test_user_sees_only_own_assets_and_list_omits_sensitive_details() -> None:
    first_token = _token("first@example.com")
    second_token = _token("second@example.com")
    _create_asset(first_token, "First Asset")
    _create_asset(second_token, "Second Asset")

    response = client.get("/assets", headers={"Authorization": f"Bearer {first_token}"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["asset_name"] == "First Asset"
    assert "details" not in payload[0]


def test_user_cannot_access_another_users_asset() -> None:
    first_token = _token("first@example.com")
    second_token = _token("second@example.com")
    created = _create_asset(second_token, "Second Asset")

    response = client.get(f"/assets/{created['id']}", headers={"Authorization": f"Bearer {first_token}"})

    assert response.status_code == 404


def test_sensitive_fields_are_encrypted_in_storage() -> None:
    token = _token("owner@example.com")
    created = _create_asset(token)

    db = SessionLocal()
    try:
        asset = db.query(Asset).filter(Asset.id == created["id"]).one()
        detail = db.query(AssetDetail).filter(AssetDetail.asset_id == asset.id).one()

        assert asset.user_id
        assert asset.created_by == asset.user_id
        assert asset.modified_by == asset.user_id
        assert detail.account_number_encrypted != "123456789"
        assert detail.policy_number_encrypted != "POL-123"
        assert detail.notes_encrypted != "Private asset note"
        assert detail.claim_instructions_encrypted != "Call the bank estate department"
    finally:
        db.close()


def test_decrypted_fields_return_only_after_authorization() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    created = _create_asset(owner_token)

    authorized = client.get(f"/assets/{created['id']}", headers={"Authorization": f"Bearer {owner_token}"})
    assert authorized.status_code == 200
    assert authorized.json()["details"] == {
        "account_number": "123456789",
        "policy_number": "POL-123",
        "notes": "Private asset note",
        "claim_instructions": "Call the bank estate department",
    }

    unauthorized = client.get(f"/assets/{created['id']}", headers={"Authorization": f"Bearer {other_token}"})
    assert unauthorized.status_code == 404


def test_asset_endpoints_require_authentication() -> None:
    assert client.get("/assets").status_code == 401
    assert client.post("/assets", json={"asset_name": "A", "asset_category": "Bank Account"}).status_code == 401


def test_owner_can_update_asset_metadata_verification_and_details() -> None:
    token = _token("owner@example.com")
    created = _create_asset(token)

    response = client.put(
        f"/assets/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "asset_name": "Updated Checking",
            "institution": "Updated Bank",
            "is_verified": True,
            "verification_status": ASSET_VERIFICATION_VERIFIED,
            "details": {
                "account_number": "987654321",
                "policy_number": "POL-999",
                "notes": "Updated private note",
                "claim_instructions": "Updated claim instructions",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset_name"] == "Updated Checking"
    assert payload["institution"] == "Updated Bank"
    assert payload["is_verified"] is True
    assert payload["verification_status"] == ASSET_VERIFICATION_VERIFIED
    assert payload["details"]["account_number"] == "987654321"
    assert payload["details"]["claim_instructions"] == "Updated claim instructions"


def test_non_owner_cannot_update_asset() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    created = _create_asset(owner_token)

    response = client.put(
        f"/assets/{created['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"asset_name": "Stolen Update"},
    )

    assert response.status_code == 404


def test_owner_can_archive_asset_and_archived_assets_are_excluded_from_list() -> None:
    token = _token("owner@example.com")
    created = _create_asset(token)

    archive = client.post(f"/assets/{created['id']}/archive", headers={"Authorization": f"Bearer {token}"})
    assert archive.status_code == 200
    assert archive.json()["status"] == ASSET_STATUS_ARCHIVED
    assert archive.json()["archived_at"] is not None

    listing = client.get("/assets", headers={"Authorization": f"Bearer {token}"})
    assert listing.status_code == 200
    assert listing.json() == []


def test_non_owner_cannot_archive_asset() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    created = _create_asset(owner_token)

    response = client.post(f"/assets/{created['id']}/archive", headers={"Authorization": f"Bearer {other_token}"})

    assert response.status_code == 404


def test_updated_sensitive_fields_remain_encrypted_in_storage() -> None:
    token = _token("owner@example.com")
    created = _create_asset(token)

    response = client.put(
        f"/assets/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"details": {"account_number": "555555555", "claim_instructions": "Updated encrypted instructions"}},
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        detail = db.query(AssetDetail).filter(AssetDetail.asset_id == created["id"]).one()
        asset = db.query(Asset).filter(Asset.id == created["id"]).one()
        assert detail.account_number_encrypted != "555555555"
        assert detail.claim_instructions_encrypted != "Updated encrypted instructions"
        assert asset.modified_by == asset.user_id
        assert asset.updated_at is not None
    finally:
        db.close()