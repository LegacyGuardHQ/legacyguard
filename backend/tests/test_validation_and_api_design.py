import os

import pytest
from pydantic import ValidationError

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.models.asset import Asset
from app.models.asset_detail import AssetDetail
from app.models.user import User
from app.schemas.legacy import AssetCreate, BeneficiaryCreate, DocumentCreate
from app.services.ownership import can_access_record, filter_by_owner
from app.services.encryption import encryption_service


@pytest.fixture(autouse=True)
def reset_db() -> None:
    from app.database.connection import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_ownership_filter_keeps_only_current_user_records() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        owner = User(id="owner", email="owner@example.com", password_hash="hash", role="USER")
        other = User(id="other", email="other@example.com", password_hash="hash", role="USER")
        db.add_all(
            [
                owner,
                other,
                Asset(id="a1", user_id=owner.id, asset_category="Bank Account", asset_name="Checking", status="Active"),
                Asset(id="a2", user_id=other.id, asset_category="Investment", asset_name="Brokerage", status="Active"),
            ]
        )
        db.commit()

        query = filter_by_owner(db.query(Asset), owner.id)
        records = query.all()
        assert len(records) == 1
        assert records[0].asset_name == "Checking"
    finally:
        db.close()


def test_ownership_guard_rejects_other_users_access() -> None:
    assert can_access_record("owner-user", "other-user") is False
    assert can_access_record("same-user", "same-user") is True


def test_asset_schema_rejects_invalid_data() -> None:
    with pytest.raises(ValidationError):
        AssetCreate(asset_name="", asset_category="", estimated_value=-1)

    with pytest.raises(ValidationError):
        AssetCreate(asset_name="Checking", asset_category="Bank Account", estimated_value=-0.01)


def test_beneficiary_and_document_schemas_reject_invalid_data() -> None:
    with pytest.raises(ValidationError):
        BeneficiaryCreate(name="", relationship_type="")

    with pytest.raises(ValidationError):
        DocumentCreate(document_type="Bad type", document_name="Statement", size_bytes=26 * 1024 * 1024)


def test_sensitive_fields_are_encrypted_and_not_stored_plaintext() -> None:
    detail = AssetDetail(asset_id="asset-1")
    detail.set_encrypted_fields(account_number="1234", policy_number="POL-1", notes="secure")

    assert detail.account_number_encrypted is not None
    assert detail.account_number_encrypted != "1234"
    assert encryption_service.decrypt(detail.account_number_encrypted) == "1234"
