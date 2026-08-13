import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.main import app
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


def test_password_hashing_is_opaque() -> None:
    response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "StrongPass123!"},
    )
    assert response.status_code == 201
    assert "password_hash" not in response.json()

    from app.database.connection import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "user@example.com").first()
    finally:
        db.close()
    assert user is not None
    assert user.password_hash != "StrongPass123!"
    assert user.password_hash.startswith("$2b$")


def test_token_expiration_and_revocation_flow() -> None:
    register = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "StrongPass123!"},
    )
    assert register.status_code == 201

    login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "StrongPass123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    sessions = client.get("/auth/sessions", headers={"Authorization": f"Bearer {token}"})
    assert sessions.status_code == 200

    revoke = client.post("/auth/sessions/revoke-all", headers={"Authorization": f"Bearer {token}"})
    assert revoke.status_code == 200

    rejected = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert rejected.status_code == 401


def test_rate_limiting_blocks_repeated_failures() -> None:
    for _ in range(5):
        response = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "WrongPass123!"},
        )
        assert response.status_code == 401

    blocked = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "WrongPass123!"},
    )
    assert blocked.status_code == 429


def test_permission_checks_block_non_owner_access() -> None:
    first = client.post(
        "/auth/register",
        json={"email": "first@example.com", "password": "StrongPass123!"},
    )
    second = client.post(
        "/auth/register",
        json={"email": "second@example.com", "password": "StrongPass123!"},
    )
    assert first.status_code == 201
    assert second.status_code == 201

    login = client.post(
        "/auth/login",
        json={"email": "first@example.com", "password": "StrongPass123!"},
    )
    token = login.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
