import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.models.asset import Asset
from app.models.user import User
from app.security.authorization import (
    ensure_owner,
    owned_record_dependency,
    require_authenticated_user,
)


@pytest.fixture(autouse=True)
def reset_db() -> None:
    from app.database.connection import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_require_authenticated_user_returns_current_user() -> None:
    user = User(id="user-a", email="a@example.com", password_hash="hash", role="USER")
    assert require_authenticated_user(user) is user


def test_ensure_owner_missing_record_raises_404() -> None:
    user = User(id="user-a", email="a@example.com", password_hash="hash", role="USER")
    with pytest.raises(HTTPException) as exc:
        ensure_owner(None, user)
    assert exc.value.status_code == 404


def test_owned_record_dependency_resolves_owned_record(db_session) -> None:
    user = User(id="user-a", email="a@example.com", password_hash="hash", role="USER")
    asset = Asset(id="asset-a", user_id=user.id, asset_category="Bank", asset_name="Checking", status="Active")
    db_session.add_all([user, asset])
    db_session.commit()

    dependency = owned_record_dependency(Asset)

    assert dependency.__name__ == "get_owned_asset"

    resolved = dependency(record_id="asset-a", current_user=user, db=db_session)
    assert resolved.id == "asset-a"


def test_owned_record_dependency_rejects_other_users_record(db_session) -> None:
    owner = User(id="owner", email="owner@example.com", password_hash="hash", role="USER")
    other = User(id="other", email="other@example.com", password_hash="hash", role="USER")
    asset = Asset(id="asset-a", user_id=owner.id, asset_category="Bank", asset_name="Checking", status="Active")
    db_session.add_all([owner, other, asset])
    db_session.commit()

    dependency = owned_record_dependency(Asset)

    with pytest.raises(HTTPException) as exc:
        dependency(record_id="asset-a", current_user=other, db=db_session)
    assert exc.value.status_code == 404
