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
from app.models.asset import ASSET_STATUS_ARCHIVED, Asset
from app.models.asset_beneficiary import AssetBeneficiary
from app.models.beneficiary import BENEFICIARY_STATUS_ACTIVE, BENEFICIARY_STATUS_ARCHIVED, BENEFICIARY_STATUS_DECEASED, BENEFICIARY_VERIFICATION_UNKNOWN, Beneficiary
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


def _create_asset(token: str, name: str = "Checking") -> dict:
    response = client.post(
        "/assets",
        headers={"Authorization": f"Bearer {token}"},
        json={"asset_name": name, "asset_category": "Bank Account", "estimated_value": "1000.00"},
    )
    assert response.status_code == 201
    return response.json()


def _create_beneficiary(token: str, name: str = "Jane Doe") -> dict:
    response = client.post(
        "/beneficiaries",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "relationship_type": "Spouse", "contact_information": "private@example.com", "notes": "Sensitive note"},
    )
    assert response.status_code == 201
    return response.json()


def _post_link(token: str, asset_id: str, beneficiary_id: str, **overrides):
    payload = {
        "beneficiary_id": beneficiary_id,
        "beneficiary_role": "PRIMARY",
        "percentage": "50.00",
        "priority_order": 1,
        "transfer_method": "WILL",
    }
    payload.update(overrides)
    return client.post(f"/assets/{asset_id}/beneficiaries", headers={"Authorization": f"Bearer {token}"}, json=payload)


def _put_link(token: str, asset_id: str, beneficiary_id: str, **overrides):
    payload = {
        "beneficiary_role": "PRIMARY",
        "percentage": "50.00",
        "priority_order": 1,
        "transfer_method": "WILL",
    }
    payload.update(overrides)
    return client.put(f"/assets/{asset_id}/beneficiaries/{beneficiary_id}", headers={"Authorization": f"Bearer {token}"}, json=payload)


def _deactivate_link(token: str, asset_id: str, beneficiary_id: str, **payload):
    return client.post(
        f"/assets/{asset_id}/beneficiaries/{beneficiary_id}/deactivate",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )


def test_owner_links_own_beneficiary_to_own_asset() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)

    response = _post_link(token, asset["id"], beneficiary["id"])

    assert response.status_code == 201
    payload = response.json()
    assert payload["asset_id"] == asset["id"]
    assert payload["beneficiary"]["id"] == beneficiary["id"]
    assert payload["beneficiary"]["status"] == BENEFICIARY_STATUS_ACTIVE
    assert payload["beneficiary"]["verification_status"] == BENEFICIARY_VERIFICATION_UNKNOWN
    assert payload["beneficiary_role"] == "PRIMARY"
    assert payload["percentage"] == "50.00"
    assert payload["transfer_method"] == "WILL"


def test_cross_user_asset_linking_blocked() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    owner_asset = _create_asset(owner_token)
    other_beneficiary = _create_beneficiary(other_token)

    response = _post_link(other_token, owner_asset["id"], other_beneficiary["id"])

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


def test_cross_user_beneficiary_linking_blocked() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    asset = _create_asset(owner_token)
    other_beneficiary = _create_beneficiary(other_token)

    response = _post_link(owner_token, asset["id"], other_beneficiary["id"])

    assert response.status_code == 404
    assert response.json()["detail"] == "Beneficiary not found"


def test_duplicate_active_links_rejected() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)
    assert _post_link(token, asset["id"], beneficiary["id"]).status_code == 201

    response = _post_link(token, asset["id"], beneficiary["id"], percentage="25")

    assert response.status_code == 409


def test_invalid_role_rejected() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)

    response = _post_link(token, asset["id"], beneficiary["id"], beneficiary_role="OWNER")

    assert response.status_code == 422


def test_invalid_transfer_method_rejected() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)

    response = _post_link(token, asset["id"], beneficiary["id"], transfer_method="EMAIL")

    assert response.status_code == 422


def test_primary_totals_above_100_rejected() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    first = _create_beneficiary(token, "First")
    second = _create_beneficiary(token, "Second")
    assert _post_link(token, asset["id"], first["id"], percentage="60").status_code == 201

    response = _post_link(token, asset["id"], second["id"], percentage="50")

    assert response.status_code == 422
    assert "PRIMARY allocation total cannot exceed 100" in response.json()["detail"]


def test_contingent_totals_validated_independently() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    primary = _create_beneficiary(token, "Primary")
    contingent_one = _create_beneficiary(token, "Contingent One")
    contingent_two = _create_beneficiary(token, "Contingent Two")
    assert _post_link(token, asset["id"], primary["id"], beneficiary_role="PRIMARY", percentage="100").status_code == 201
    assert _post_link(token, asset["id"], contingent_one["id"], beneficiary_role="CONTINGENT", percentage="60").status_code == 201

    response = _post_link(token, asset["id"], contingent_two["id"], beneficiary_role="CONTINGENT", percentage="50")


    assert response.status_code == 422
    assert "CONTINGENT allocation total cannot exceed 100" in response.json()["detail"]


def test_informational_links_ignored_for_percentage_totals() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    info = _create_beneficiary(token, "Info")
    primary = _create_beneficiary(token, "Primary")
    assert _post_link(token, asset["id"], info["id"], beneficiary_role="INFORMATIONAL", percentage="100").status_code == 201

    response = _post_link(token, asset["id"], primary["id"], beneficiary_role="PRIMARY", percentage="100")

    assert response.status_code == 201


def test_get_returns_only_active_links() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    active = _create_beneficiary(token, "Active")
    inactive = _create_beneficiary(token, "Inactive")
    active_link = _post_link(token, asset["id"], active["id"], percentage="40")
    inactive_link = _post_link(token, asset["id"], inactive["id"], percentage="40")
    assert active_link.status_code == 201
    assert inactive_link.status_code == 201

    db = SessionLocal()
    try:
        link = db.query(AssetBeneficiary).filter(AssetBeneficiary.id == inactive_link.json()["id"]).one()
        link.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.get(f"/assets/{asset['id']}/beneficiaries", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert [item["beneficiary"]["id"] for item in payload] == [active["id"]]


def test_sensitive_beneficiary_fields_are_not_included() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)
    assert _post_link(token, asset["id"], beneficiary["id"]).status_code == 201

    response = client.get(f"/assets/{asset['id']}/beneficiaries", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    linked_beneficiary = response.json()[0]["beneficiary"]
    assert "contact_information" not in linked_beneficiary
    assert "contact_information_encrypted" not in linked_beneficiary
    assert "notes" not in linked_beneficiary
    assert "notes_encrypted" not in linked_beneficiary


def test_owner_can_update_role_percentage_priority_and_transfer_method() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)
    assert _post_link(token, asset["id"], beneficiary["id"], percentage="25").status_code == 201

    response = _put_link(
        token,
        asset["id"],
        beneficiary["id"],
        beneficiary_role="CONTINGENT",
        percentage="75.00",
        priority_order=3,
        transfer_method="TRUST",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["beneficiary_role"] == "CONTINGENT"
    assert payload["percentage"] == "75.00"
    assert payload["priority_order"] == 3
    assert payload["transfer_method"] == "TRUST"
    assert "contact_information" not in payload["beneficiary"]
    assert "notes" not in payload["beneficiary"]


def test_non_owner_cannot_update_link() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    asset = _create_asset(owner_token)
    beneficiary = _create_beneficiary(owner_token)
    assert _post_link(owner_token, asset["id"], beneficiary["id"]).status_code == 201

    response = _put_link(other_token, asset["id"], beneficiary["id"], percentage="25")

    assert response.status_code == 404


def test_allocation_totals_recalculated_correctly_on_update() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    first = _create_beneficiary(token, "First")
    second = _create_beneficiary(token, "Second")
    assert _post_link(token, asset["id"], first["id"], percentage="40").status_code == 201
    assert _post_link(token, asset["id"], second["id"], percentage="40").status_code == 201

    response = _put_link(token, asset["id"], second["id"], percentage="70")

    assert response.status_code == 422
    assert "PRIMARY allocation total cannot exceed 100" in response.json()["detail"]


def test_update_does_not_double_count_old_percentage() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)
    assert _post_link(token, asset["id"], beneficiary["id"], percentage="60").status_code == 201

    response = _put_link(token, asset["id"], beneficiary["id"], percentage="80")

    assert response.status_code == 200
    assert response.json()["percentage"] == "80.00"


def test_invalid_update_role_and_transfer_method_rejected() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)
    assert _post_link(token, asset["id"], beneficiary["id"]).status_code == 201

    role_response = _put_link(token, asset["id"], beneficiary["id"], beneficiary_role="OWNER")
    transfer_response = _put_link(token, asset["id"], beneficiary["id"], transfer_method="EMAIL")

    assert role_response.status_code == 422
    assert transfer_response.status_code == 422


def test_owner_can_deactivate_link() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)
    link_response = _post_link(token, asset["id"], beneficiary["id"], percentage="60", transfer_method="TRUST")
    assert link_response.status_code == 201

    response = _deactivate_link(token, asset["id"], beneficiary["id"], deactivation_reason="Changed estate plan")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == link_response.json()["id"]
    assert payload["asset_id"] == asset["id"]
    assert payload["beneficiary_id"] == beneficiary["id"]
    assert payload["is_active"] is False
    assert "deactivation_reason" not in payload
    assert "deactivation_reason_encrypted" not in payload

    db = SessionLocal()
    try:
        link = db.query(AssetBeneficiary).filter(AssetBeneficiary.id == payload["id"]).one()
        assert link.is_active is False
        assert link.deactivated_at is not None
        assert link.beneficiary_role == "PRIMARY"
        assert str(link.percentage) == "60.00"
        assert link.transfer_method == "TRUST"
        assert link.deactivation_reason_encrypted is not None
        assert link.get_deactivation_reason() == "Changed estate plan"
    finally:
        db.close()


def test_deactivated_link_is_excluded_from_get_responses_and_allocation_totals() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    first = _create_beneficiary(token, "First")
    second = _create_beneficiary(token, "Second")
    assert _post_link(token, asset["id"], first["id"], percentage="100").status_code == 201
    assert _deactivate_link(token, asset["id"], first["id"]).status_code == 200

    list_response = client.get(f"/assets/{asset['id']}/beneficiaries", headers={"Authorization": f"Bearer {token}"})
    create_response = _post_link(token, asset["id"], second["id"], percentage="100")

    assert list_response.status_code == 200
    assert list_response.json() == []
    assert create_response.status_code == 201


def test_non_owner_cannot_deactivate_link() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    asset = _create_asset(owner_token)
    beneficiary = _create_beneficiary(owner_token)
    assert _post_link(owner_token, asset["id"], beneficiary["id"]).status_code == 201

    response = _deactivate_link(other_token, asset["id"], beneficiary["id"])

    assert response.status_code == 404


def test_archived_assets_cannot_have_links_updated() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)
    assert _post_link(token, asset["id"], beneficiary["id"]).status_code == 201

    db = SessionLocal()
    try:
        db_asset = db.query(Asset).filter(Asset.id == asset["id"]).one()
        db_asset.status = ASSET_STATUS_ARCHIVED
        db.commit()
    finally:
        db.close()

    response = _put_link(token, asset["id"], beneficiary["id"], percentage="25")

    assert response.status_code == 400
    assert "Archived assets" in response.json()["detail"]


def test_archived_beneficiaries_cannot_have_links_updated() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)
    assert _post_link(token, asset["id"], beneficiary["id"]).status_code == 201

    db = SessionLocal()
    try:
        db_beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary["id"]).one()
        db_beneficiary.status = BENEFICIARY_STATUS_ARCHIVED
        db.commit()
    finally:
        db.close()

    response = _put_link(token, asset["id"], beneficiary["id"], percentage="25")

    assert response.status_code == 400
    assert "Archived beneficiaries" in response.json()["detail"]


def test_deceased_beneficiary_links_are_viewable_but_cannot_be_updated_active_recipients() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)
    assert _post_link(token, asset["id"], beneficiary["id"]).status_code == 201

    db = SessionLocal()
    try:
        db_beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary["id"]).one()
        db_beneficiary.is_deceased = True
        db_beneficiary.status = BENEFICIARY_STATUS_DECEASED
        db.commit()
    finally:
        db.close()

    list_response = client.get(f"/assets/{asset['id']}/beneficiaries", headers={"Authorization": f"Bearer {token}"})
    update_response = _put_link(token, asset["id"], beneficiary["id"], percentage="25")
    deactivate_response = _deactivate_link(token, asset["id"], beneficiary["id"])

    assert list_response.status_code == 200
    assert list_response.json()[0]["beneficiary"]["is_deceased"] is True
    assert update_response.status_code == 400
    assert "Deceased beneficiaries" in update_response.json()["detail"]
    assert deactivate_response.status_code == 200


def test_relinking_reactivates_existing_inactive_link() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)
    original = _post_link(token, asset["id"], beneficiary["id"], percentage="30")
    assert original.status_code == 201
    assert _deactivate_link(token, asset["id"], beneficiary["id"]).status_code == 200

    response = _post_link(token, asset["id"], beneficiary["id"], percentage="45", beneficiary_role="SUCCESSOR")

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == original.json()["id"]
    assert payload["beneficiary_role"] == "SUCCESSOR"
    assert payload["percentage"] == "45.00"