import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event

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


def test_simultaneous_primary_allocations_cannot_exceed_100_on_postgres(monkeypatch) -> None:
    """Concurrent API requests must not both accept allocations totaling 120%."""
    from app.database.connection import engine
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row-locking and separate concurrent transactions")

    from app.api import asset_beneficiaries as links_api

    token = _token("concurrent-allocations@example.com")
    asset = _create_asset(token)
    first = _create_beneficiary(token, "Concurrent First")
    second = _create_beneficiary(token, "Concurrent Second")

    first_validated = Event()
    second_completed = Event()
    original_validate = links_api.validate_asset_allocation_change

    def coordinated_validate(db, asset_id, role, percentage, *, link_id=None):
        result = original_validate(db, asset_id, role, percentage, link_id=link_id)
        if not first_validated.is_set():
            first_validated.set()
            # Keep the first request before commit long enough for the other
            # request to attempt validation. Under a per-asset row lock, that
            # second request must wait until the first commits.
            second_completed.wait(timeout=2)
        return result

    monkeypatch.setattr(links_api, "validate_asset_allocation_change", coordinated_validate)

    def post_for(beneficiary_id: str):
        with TestClient(app) as request_client:
            return request_client.post(
                f"/assets/{asset['id']}/beneficiaries",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "beneficiary_id": beneficiary_id,
                    "beneficiary_role": "PRIMARY",
                    "percentage": "60.00",
                    "priority_order": 1,
                    "transfer_method": "WILL",
                },
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_request = pool.submit(post_for, first["id"])
        assert first_validated.wait(timeout=10), "First request never reached allocation validation"
        second_request = pool.submit(post_for, second["id"])
        try:
            second_response = second_request.result(timeout=15)
        finally:
            second_completed.set()
        first_response = first_request.result(timeout=15)

    assert sorted([first_response.status_code, second_response.status_code]) == [201, 422]
    db = SessionLocal()
    try:
        links = db.query(AssetBeneficiary).filter(
            AssetBeneficiary.asset_id == asset["id"],
            AssetBeneficiary.is_active.is_(True),
            AssetBeneficiary.beneficiary_role == "PRIMARY",
        ).all()
        assert sum((Decimal(str(link.percentage)) for link in links), Decimal("0")) <= Decimal("100")
    finally:
        db.close()


def _exercise_two_competing_postgres_mutations(monkeypatch, first_request, second_request):
    """Let the second request reach validation while the first holds its lock."""
    from app.api import asset_beneficiaries as links_api

    first_validated = Event()
    second_entered_validation = Event()
    original_validate = links_api.validate_asset_allocation_change

    def coordinated_validate(db, asset_id, role, percentage, *, link_id=None):
        # The first request owns the asset lock after successful validation.
        # The second announces itself before trying to obtain that lock.
        if first_validated.is_set():
            second_entered_validation.set()
        result = original_validate(db, asset_id, role, percentage, link_id=link_id)
        if not first_validated.is_set():
            first_validated.set()
            assert second_entered_validation.wait(timeout=10), (
                "Second request did not reach allocation validation"
            )
        return result

    monkeypatch.setattr(links_api, "validate_asset_allocation_change", coordinated_validate)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(first_request)
        assert first_validated.wait(timeout=10), "First request did not validate"
        second_future = pool.submit(second_request)
        first_response = first_future.result(timeout=20)
        second_response = second_future.result(timeout=20)
    return first_response, second_response


def _assert_active_primary_allocation_total_within_limit(asset_id: str) -> None:
    db = SessionLocal()
    try:
        links = db.query(AssetBeneficiary).filter(
            AssetBeneficiary.asset_id == asset_id,
            AssetBeneficiary.is_active.is_(True),
            AssetBeneficiary.beneficiary_role == "PRIMARY",
        ).all()
        total = sum((Decimal(str(link.percentage)) for link in links), Decimal("0"))
        assert total <= Decimal("100")
    finally:
        db.close()


def test_concurrent_existing_allocation_updates_are_serialized_on_postgres(monkeypatch) -> None:
    from app.database.connection import engine
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL concurrent transactions")

    token = _token("update-race@example.com")
    asset = _create_asset(token)
    first = _create_beneficiary(token, "First Update")
    second = _create_beneficiary(token, "Second Update")
    assert _post_link(token, asset["id"], first["id"], percentage="30").status_code == 201
    assert _post_link(token, asset["id"], second["id"], percentage="30").status_code == 201

    def update_first():
        with TestClient(app) as worker:
            return worker.put(
                f"/assets/{asset['id']}/beneficiaries/{first['id']}",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "beneficiary_role": "PRIMARY", "percentage": "70.00",
                    "priority_order": 1, "transfer_method": "WILL",
                },
            )

    def update_second():
        with TestClient(app) as worker:
            return worker.put(
                f"/assets/{asset['id']}/beneficiaries/{second['id']}",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "beneficiary_role": "PRIMARY", "percentage": "70.00",
                    "priority_order": 1, "transfer_method": "WILL",
                },
            )

    first_response, second_response = _exercise_two_competing_postgres_mutations(
        monkeypatch, update_first, update_second
    )
    assert (first_response.status_code, second_response.status_code) == (200, 422)
    _assert_active_primary_allocation_total_within_limit(asset["id"])


def test_concurrent_reactivation_and_update_are_serialized_on_postgres(monkeypatch) -> None:
    from app.database.connection import engine
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL concurrent transactions")

    token = _token("reactivation-race@example.com")
    asset = _create_asset(token)
    inactive = _create_beneficiary(token, "Inactive Recipient")
    active = _create_beneficiary(token, "Active Recipient")
    assert _post_link(token, asset["id"], inactive["id"], percentage="60").status_code == 201
    assert _deactivate_link(token, asset["id"], inactive["id"]).status_code == 200
    assert _post_link(token, asset["id"], active["id"], percentage="30").status_code == 201

    def reactivate_first():
        with TestClient(app) as worker:
            return worker.post(
                f"/assets/{asset['id']}/beneficiaries",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "beneficiary_id": inactive["id"], "beneficiary_role": "PRIMARY",
                    "percentage": "60.00", "priority_order": 1, "transfer_method": "WILL",
                },
            )

    def update_second():
        with TestClient(app) as worker:
            return worker.put(
                f"/assets/{asset['id']}/beneficiaries/{active['id']}",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "beneficiary_role": "PRIMARY", "percentage": "50.00",
                    "priority_order": 1, "transfer_method": "WILL",
                },
            )

    first_response, second_response = _exercise_two_competing_postgres_mutations(
        monkeypatch, reactivate_first, update_second
    )
    assert (first_response.status_code, second_response.status_code) == (201, 422)
    _assert_active_primary_allocation_total_within_limit(asset["id"])


def test_concurrent_updates_same_link_refresh_locked_state_on_postgres(monkeypatch) -> None:
    """A waiter must observe the first update after obtaining the asset lock."""
    from app.database.connection import engine
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL concurrent transactions")

    from app.api import asset_beneficiaries as links_api

    token = _token("same-link-race@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token, "Shared Recipient")
    created = _post_link(token, asset["id"], beneficiary["id"], percentage="30")
    assert created.status_code == 201
    link_id = created.json()["id"]

    first_validated = Event()
    second_entered = Event()
    original_validate = links_api.validate_asset_allocation_change
    second_observed_percentage = []

    def coordinated_validate(db, asset_id, role, percentage, *, link_id=None):
        is_second = first_validated.is_set()
        if is_second:
            second_entered.set()
        result = original_validate(db, asset_id, role, percentage, link_id=link_id)
        if is_second:
            # The API loaded this same link before waiting on the parent lock.
            # The post-lock read must refresh that ORM identity-map instance.
            second_observed_percentage.append(
                Decimal(str(db.get(AssetBeneficiary, link_id).percentage))
            )
        else:
            first_validated.set()
            assert second_entered.wait(timeout=10), "Second update never attempted validation"
        return result

    monkeypatch.setattr(links_api, "validate_asset_allocation_change", coordinated_validate)

    def update_to(value):
        with TestClient(app) as worker:
            return worker.put(
                f"/assets/{asset['id']}/beneficiaries/{beneficiary['id']}",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "beneficiary_role": "PRIMARY", "percentage": value,
                    "priority_order": 1, "transfer_method": "WILL",
                },
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(update_to, "50.00")
        assert first_validated.wait(timeout=10), "First update never validated"
        second_future = pool.submit(update_to, "60.00")
        first_response = first_future.result(timeout=20)
        second_response = second_future.result(timeout=20)

    assert (first_response.status_code, second_response.status_code) == (200, 200)
    assert second_observed_percentage == [Decimal("50.00")]
    db = SessionLocal()
    try:
        stored = db.query(AssetBeneficiary).filter(AssetBeneficiary.id == link_id).one()
        assert Decimal(str(stored.percentage)) == Decimal("60.00")
    finally:
        db.close()
    _assert_active_primary_allocation_total_within_limit(asset["id"])


@pytest.mark.parametrize("role", ["PRIMARY", "INFORMATIONAL"])
def test_concurrent_reactivation_of_same_link_rejects_duplicate_on_postgres(monkeypatch, role: str) -> None:
    """Two requests must not both reactivate the same inactive link."""
    from app.database.connection import engine
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL concurrent transactions")

    token = _token("same-reactivation-race@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token, "Reactivated Recipient")
    created = _post_link(token, asset["id"], beneficiary["id"], percentage="25", beneficiary_role=role)
    assert created.status_code == 201
    assert _deactivate_link(token, asset["id"], beneficiary["id"]).status_code == 200
    link_id = created.json()["id"]

    def reactivate(percentage):
        with TestClient(app) as worker:
            return worker.post(
                f"/assets/{asset['id']}/beneficiaries",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "beneficiary_id": beneficiary["id"],
                    "beneficiary_role": role,
                    "percentage": percentage,
                    "priority_order": 1,
                    "transfer_method": "WILL",
                },
            )

    first, second = _exercise_two_competing_postgres_mutations(
        monkeypatch,
        lambda: reactivate("40.00"),
        lambda: reactivate("50.00"),
    )
    assert (first.status_code, second.status_code) == (201, 409)
    db = SessionLocal()
    try:
        links = db.query(AssetBeneficiary).filter(
            AssetBeneficiary.asset_id == asset["id"],
            AssetBeneficiary.beneficiary_id == beneficiary["id"],
        ).all()
        assert len(links) == 1
        assert links[0].id == link_id
        assert links[0].is_active is True
        assert Decimal(str(links[0].percentage)) == Decimal("40.00")
    finally:
        db.close()
    _assert_active_primary_allocation_total_within_limit(asset["id"])


@pytest.mark.parametrize("role", ["PRIMARY", "INFORMATIONAL"])
def test_concurrent_creation_of_same_new_link_returns_conflict_on_postgres(monkeypatch, role: str) -> None:
    """A losing same-pair create request must respond 409, not raise IntegrityError."""
    from app.database.connection import engine
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL concurrent transactions")

    token = _token(f"new-link-race-{role.lower()}@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token, "New Recipient")

    def create_link(percentage: str):
        with TestClient(app) as worker:
            return worker.post(
                f"/assets/{asset['id']}/beneficiaries",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "beneficiary_id": beneficiary["id"],
                    "beneficiary_role": role,
                    "percentage": percentage,
                    "priority_order": 1,
                    "transfer_method": "WILL",
                },
            )

    first, second = _exercise_two_competing_postgres_mutations(
        monkeypatch,
        lambda: create_link("40.00"),
        lambda: create_link("50.00"),
    )
    assert (first.status_code, second.status_code) == (201, 409)
    db = SessionLocal()
    try:
        links = db.query(AssetBeneficiary).filter(
            AssetBeneficiary.asset_id == asset["id"],
            AssetBeneficiary.beneficiary_id == beneficiary["id"],
        ).all()
        assert len(links) == 1
        assert links[0].is_active is True
        assert Decimal(str(links[0].percentage)) == Decimal("40.00")
    finally:
        db.close()
    _assert_active_primary_allocation_total_within_limit(asset["id"])


def test_asset_archived_during_link_update_is_rejected_on_postgres(monkeypatch) -> None:
    """An archive committed after the initial lifecycle check must block the update."""
    from app.database.connection import engine
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL concurrent transactions")

    from app.api import asset_beneficiaries as links_api

    token = _token("concurrent-asset-archive@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token, "Archive Race Recipient")
    assert _post_link(token, asset["id"], beneficiary["id"], percentage="30").status_code == 201

    checked_lifecycle = Event()
    archive_committed = Event()
    original_check = links_api.validate_link_lifecycle_for_mutation

    def pause_after_lifecycle_check(asset_obj, beneficiary_obj):
        original_check(asset_obj, beneficiary_obj)
        checked_lifecycle.set()
        assert archive_committed.wait(timeout=10), "Asset archive did not complete"

    monkeypatch.setattr(links_api, "validate_link_lifecycle_for_mutation", pause_after_lifecycle_check)

    def update_link():
        with TestClient(app) as worker:
            return worker.put(
                f"/assets/{asset['id']}/beneficiaries/{beneficiary['id']}",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "beneficiary_role": "PRIMARY",
                    "percentage": "50.00",
                    "priority_order": 1,
                    "transfer_method": "WILL",
                },
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending_update = pool.submit(update_link)
        try:
            assert checked_lifecycle.wait(timeout=10), "Update did not reach lifecycle validation"
            with TestClient(app) as archive_client:
                archived = archive_client.post(
                    f"/assets/{asset['id']}/archive",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert archived.status_code == 200
            assert archived.json()["status"] == ASSET_STATUS_ARCHIVED
        finally:
            archive_committed.set()
        updated = pending_update.result(timeout=20)

    assert updated.status_code == 400
    assert "Archived assets" in updated.json()["detail"]

    db = SessionLocal()
    try:
        stored = db.query(AssetBeneficiary).filter(
            AssetBeneficiary.asset_id == asset["id"],
            AssetBeneficiary.beneficiary_id == beneficiary["id"],
        ).one()
        assert Decimal(str(stored.percentage)) == Decimal("30.00")
    finally:
        db.close()
