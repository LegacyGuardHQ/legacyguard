import os
from datetime import datetime, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from passlib.exc import PasswordTruncateError

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.main import app
from app.config import settings
from app.database.connection import SessionLocal
from app.models.audit_log import AuditLog
from app.models.session import UserSession
from app.security.auth import create_access_token, create_refresh_token, get_password_hash, verify_password
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


def test_user_registration_and_login() -> None:
    response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "StrongPass123!"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "user@example.com"
    assert "password_hash" not in payload

    login_response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["access_token"]
    assert login_response.json()["refresh_token"]

    db = SessionLocal()
    try:
        assert db.query(AuditLog).filter(AuditLog.event_type == "ACCOUNT_CREATED").count() == 1
        assert db.query(AuditLog).filter(AuditLog.event_type == "LOGIN_SUCCESS").count() == 1
    finally:
        db.close()


def test_ordinary_password_hashing_round_trip() -> None:
    password = "StrongPass123!"

    password_hash = get_password_hash(password)

    assert password_hash.startswith("$2b$")
    assert verify_password(password, password_hash) is True
    assert verify_password("WrongPass123!", password_hash) is False


def test_password_hashing_rejects_values_beyond_bcrypt_byte_limit() -> None:
    with pytest.raises(PasswordTruncateError):
        get_password_hash("A1!" + "a" * 70)


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

    db = SessionLocal()
    try:
        assert db.query(AuditLog).filter(AuditLog.event_type == "LOGIN_FAILED").count() == 1
    finally:
        db.close()


def test_logout_persists_revocation_and_audit_event() -> None:
    client.post(
        "/auth/register",
        json={"email": "logout@example.com", "password": "StrongPass123!"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "logout@example.com", "password": "StrongPass123!"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Logout successful"}

    db = SessionLocal()
    try:
        session = db.query(UserSession).one()
        assert session.revoked_at is not None
        assert db.query(AuditLog).filter(AuditLog.event_type == "LOGOUT").count() == 1
    finally:
        db.close()


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
