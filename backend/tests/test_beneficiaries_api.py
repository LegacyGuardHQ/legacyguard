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
from app.models.beneficiary import Beneficiary
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


def _create_beneficiary(token: str, name: str = "Jane Doe") -> dict:
    response = client.post(
        "/beneficiaries",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "relationship_type": "Spouse",
            "contact_information": "jane@example.com, 555-0100",
            "notes": "Private beneficiary note",
            "verification_status": "NEEDS_REVIEW",
            "is_deceased": False,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_authenticated_user_creates_beneficiary() -> None:
    token = _token("owner@example.com")

    payload = _create_beneficiary(token)

    assert payload["id"]
    assert payload["name"] == "Jane Doe"
    assert payload["relationship_type"] == "Spouse"
    assert payload["contact_information"] == "jane@example.com, 555-0100"
    assert payload["notes"] == "Private beneficiary note"
    assert "user_id" not in payload
    assert "created_by" not in payload
    assert "modified_by" not in payload


def test_user_can_retrieve_own_beneficiary() -> None:
    token = _token("owner@example.com")
    created = _create_beneficiary(token)

    response = client.get(f"/beneficiaries/{created['id']}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == created["id"]
    assert payload["name"] == "Jane Doe"
    assert payload["contact_information"] == "jane@example.com, 555-0100"
    assert payload["notes"] == "Private beneficiary note"


def test_user_only_sees_own_beneficiaries() -> None:
    first_token = _token("first@example.com")
    second_token = _token("second@example.com")
    _create_beneficiary(first_token, "First Beneficiary")
    _create_beneficiary(second_token, "Second Beneficiary")

    response = client.get("/beneficiaries", headers={"Authorization": f"Bearer {first_token}"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "First Beneficiary"


def test_list_responses_do_not_expose_sensitive_fields() -> None:
    token = _token("owner@example.com")
    _create_beneficiary(token)

    response = client.get("/beneficiaries", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert "contact_information" not in payload[0]
    assert "notes" not in payload[0]
    assert "contact_information_encrypted" not in payload[0]
    assert "notes_encrypted" not in payload[0]


def test_cross_user_beneficiary_access_returns_404() -> None:
    first_token = _token("first@example.com")
    second_token = _token("second@example.com")
    created = _create_beneficiary(second_token, "Second Beneficiary")

    response = client.get(f"/beneficiaries/{created['id']}", headers={"Authorization": f"Bearer {first_token}"})

    assert response.status_code == 404


def test_sensitive_contact_information_is_encrypted_in_storage() -> None:
    token = _token("owner@example.com")
    created = _create_beneficiary(token)

    db = SessionLocal()
    try:
        beneficiary = db.query(Beneficiary).filter(Beneficiary.id == created["id"]).one()
        assert beneficiary.user_id
        assert beneficiary.created_by == beneficiary.user_id
        assert beneficiary.modified_by == beneficiary.user_id
        assert beneficiary.contact_information_encrypted != "jane@example.com, 555-0100"
        assert beneficiary.contact_information_encrypted is not None
        assert "contact_information" not in Beneficiary.__table__.c
    finally:
        db.close()


def test_sensitive_notes_are_encrypted_in_storage() -> None:
    token = _token("owner@example.com")
    created = _create_beneficiary(token)

    db = SessionLocal()
    try:
        beneficiary = db.query(Beneficiary).filter(Beneficiary.id == created["id"]).one()
        assert beneficiary.notes_encrypted != "Private beneficiary note"
        assert beneficiary.notes_encrypted is not None
        assert "notes" not in Beneficiary.__table__.c
    finally:
        db.close()


def test_unauthorized_users_cannot_decrypt_beneficiary_data() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    created = _create_beneficiary(owner_token)

    authorized = client.get(f"/beneficiaries/{created['id']}", headers={"Authorization": f"Bearer {owner_token}"})
    assert authorized.status_code == 200
    assert authorized.json()["contact_information"] == "jane@example.com, 555-0100"
    assert authorized.json()["notes"] == "Private beneficiary note"

    unauthorized = client.get(f"/beneficiaries/{created['id']}", headers={"Authorization": f"Bearer {other_token}"})
    assert unauthorized.status_code == 404


def test_beneficiary_endpoints_require_authentication() -> None:
    assert client.get("/beneficiaries").status_code == 401
    assert client.get("/beneficiaries/some-beneficiary-id").status_code == 401
    assert client.post("/beneficiaries", json={"name": "Jane Doe"}).status_code == 401


def test_owner_can_update_beneficiary_metadata() -> None:
    token = _token("owner@example.com")
    created = _create_beneficiary(token)

    response = client.put(
        f"/beneficiaries/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Jane Updated",
            "relationship_type": "Sibling",
            "verification_status": "VERIFIED",
            "review_due_at": "2030-01-01T00:00:00Z",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Jane Updated"
    assert payload["relationship_type"] == "Sibling"
    assert payload["verification_status"] == "VERIFIED"
    assert payload["verified_at"] is not None
    assert payload["review_due_at"] is not None


def test_owner_can_update_encrypted_contact_information_and_notes() -> None:
    token = _token("owner@example.com")
    created = _create_beneficiary(token)

    response = client.put(
        f"/beneficiaries/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"contact_information": "updated@example.com", "notes": "Updated private note"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["contact_information"] == "updated@example.com"
    assert payload["notes"] == "Updated private note"


def test_updated_sensitive_values_remain_encrypted_in_storage() -> None:
    token = _token("owner@example.com")
    created = _create_beneficiary(token)

    response = client.put(
        f"/beneficiaries/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"contact_information": "updated@example.com", "notes": "Updated private note"},
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        beneficiary = db.query(Beneficiary).filter(Beneficiary.id == created["id"]).one()
        assert beneficiary.contact_information_encrypted != "updated@example.com"
        assert beneficiary.notes_encrypted != "Updated private note"
        assert "contact_information" not in Beneficiary.__table__.c
        assert "notes" not in Beneficiary.__table__.c
        assert beneficiary.modified_by == beneficiary.user_id
    finally:
        db.close()


def test_non_owner_cannot_update_beneficiary() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    created = _create_beneficiary(owner_token)

    response = client.put(
        f"/beneficiaries/{created['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"name": "Unauthorized Update"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Beneficiary not found"


def test_owner_can_archive_beneficiary() -> None:
    token = _token("owner@example.com")
    created = _create_beneficiary(token)

    response = client.post(f"/beneficiaries/{created['id']}/archive", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "Archived"
    assert payload["archived_at"] is not None

    db = SessionLocal()
    try:
        beneficiary = db.query(Beneficiary).filter(Beneficiary.id == created["id"]).one()
        assert beneficiary.contact_information_encrypted is not None
        assert beneficiary.notes_encrypted is not None
        assert beneficiary.modified_by == beneficiary.user_id
    finally:
        db.close()


def test_archived_beneficiary_is_excluded_from_default_list() -> None:
    token = _token("owner@example.com")
    created = _create_beneficiary(token)
    archive = client.post(f"/beneficiaries/{created['id']}/archive", headers={"Authorization": f"Bearer {token}"})
    assert archive.status_code == 200

    response = client.get("/beneficiaries", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == []


def test_non_owner_cannot_archive_beneficiary() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    created = _create_beneficiary(owner_token)

    response = client.post(f"/beneficiaries/{created['id']}/archive", headers={"Authorization": f"Bearer {other_token}"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Beneficiary not found"


def test_owner_can_mark_beneficiary_deceased() -> None:
    token = _token("owner@example.com")
    created = _create_beneficiary(token)

    response = client.post(f"/beneficiaries/{created['id']}/mark-deceased", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_deceased"] is True
    assert payload["status"] == "Deceased"


def test_deceased_timestamp_and_lifecycle_fields_are_set() -> None:
    token = _token("owner@example.com")
    created = _create_beneficiary(token)

    response = client.post(f"/beneficiaries/{created['id']}/mark-deceased", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["deceased_at"] is not None
    assert payload["verification_status"] == "NEEDS_REVIEW"

    db = SessionLocal()
    try:
        beneficiary = db.query(Beneficiary).filter(Beneficiary.id == created["id"]).one()
        assert beneficiary.is_deceased is True
        assert beneficiary.status == "Deceased"
        assert beneficiary.deceased_at is not None
        assert beneficiary.verification_status == "NEEDS_REVIEW"
        assert beneficiary.modified_by == beneficiary.user_id
    finally:
        db.close()


def test_non_owner_cannot_mark_beneficiary_deceased() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    created = _create_beneficiary(owner_token)

    response = client.post(f"/beneficiaries/{created['id']}/mark-deceased", headers={"Authorization": f"Bearer {other_token}"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Beneficiary not found"
