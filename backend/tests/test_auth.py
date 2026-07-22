import os
from datetime import datetime, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.main import app
from app.config import settings
from app.security.auth import create_access_token, create_refresh_token

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    from app.database.connection import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_user_registration_and_login() -> None:
    response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "StrongPass123!"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "user@example.com"
    assert "password_hash" in payload

    login_response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["access_token"]
    assert login_response.json()["refresh_token"]


def test_access_and_refresh_token_creation_include_unique_identifiers_and_expiration() -> None:
    first_access = create_access_token("user-1")
    second_access = create_access_token("user-1")
    refresh = create_refresh_token("user-1")

    first_payload = jwt.decode(first_access, settings.jwt_secret, algorithms=["HS256"])
    second_payload = jwt.decode(second_access, settings.jwt_secret, algorithms=["HS256"])
    refresh_payload = jwt.decode(refresh, settings.jwt_secret, algorithms=["HS256"])

    assert first_payload["typ"] == "access"
    assert refresh_payload["typ"] == "refresh"
    assert first_payload["jti"] != second_payload["jti"]
    assert first_payload["exp"] > int(datetime.now(timezone.utc).timestamp())
    assert refresh_payload["exp"] > first_payload["exp"]


def test_login_failure_with_invalid_password() -> None:
    client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "StrongPass123!"},
    )

    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "WrongPass123!"},
    )
    assert response.status_code == 401


def test_protected_route_requires_authentication() -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_invalid_token_is_rejected() -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401


def test_password_hashing_is_not_plaintext() -> None:
    response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "StrongPass123!"},
    )
    payload = response.json()
    assert payload["password_hash"] != "StrongPass123!"
    assert payload["password_hash"].startswith("$2b$")
