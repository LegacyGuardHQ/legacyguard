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
from app.api import auth as auth_api
from app.config import settings
from app.database.connection import SessionLocal
from app.models.audit_log import AuditLog
from app.models.session import UserSession
from app.models.user import User
from app.security.auth import create_access_token, get_password_hash, verify_password
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
    assert payload == {
        "message": "If registration is available for this address, you can sign in with the submitted credentials."
    }
    assert "password_hash" not in payload

    login_response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["access_token"]
    assert "refresh_token" not in login_response.json()

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


def test_access_token_creation_includes_unique_identifiers_and_expiration() -> None:
    first_access = create_access_token("user-1")
    second_access = create_access_token("user-1")

    first_payload = jwt.decode(first_access, settings.jwt_secret, algorithms=["HS256"])
    second_payload = jwt.decode(second_access, settings.jwt_secret, algorithms=["HS256"])

    assert first_payload["typ"] == "access"
    assert first_payload["jti"] != second_payload["jti"]
    assert first_payload["exp"] > int(datetime.now(timezone.utc).timestamp())


def test_login_session_expiration_matches_short_lived_access_token_policy() -> None:
    client.post(
        "/auth/register",
        json={"email": "session-expiry@example.com", "password": "StrongPass123!"},
    )

    before_login = datetime.now(timezone.utc)
    response = client.post(
        "/auth/login",
        json={"email": "session-expiry@example.com", "password": "StrongPass123!"},
    )

    assert response.status_code == 200
    db = SessionLocal()
    try:
        session = db.query(UserSession).one()
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    finally:
        db.close()

    expected_seconds = settings.access_token_expire_minutes * 60
    assert expected_seconds - 5 <= (expires_at - before_login).total_seconds() <= expected_seconds + 5


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


def test_missing_user_login_performs_dummy_bcrypt_verification(monkeypatch) -> None:
    observed_hashes: list[str] = []
    real_verify_password = auth_api.verify_password

    def observe_verification(password: str, password_hash: str) -> bool:
        observed_hashes.append(password_hash)
        return real_verify_password(password, password_hash)

    monkeypatch.setattr(auth_api, "verify_password", observe_verification)

    response = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "WrongPass123!"},
    )

    assert response.status_code == 401
    assert observed_hashes == [auth_api.DUMMY_PASSWORD_HASH]
    assert real_verify_password("WrongPass123!", auth_api.DUMMY_PASSWORD_HASH) is False


def test_existing_user_failure_verifies_the_stored_hash(monkeypatch) -> None:
    client.post(
        "/auth/register",
        json={"email": "existing@example.com", "password": "StrongPass123!"},
    )
    db = SessionLocal()
    try:
        stored_hash = db.query(User.password_hash).filter(User.email == "existing@example.com").scalar()
    finally:
        db.close()

    observed_hashes: list[str] = []
    real_verify_password = auth_api.verify_password

    def observe_verification(password: str, password_hash: str) -> bool:
        observed_hashes.append(password_hash)
        return real_verify_password(password, password_hash)

    monkeypatch.setattr(auth_api, "verify_password", observe_verification)

    response = client.post(
        "/auth/login",
        json={"email": "existing@example.com", "password": "WrongPass123!"},
    )

    assert response.status_code == 401
    assert observed_hashes == [stored_hash]
    assert stored_hash != auth_api.DUMMY_PASSWORD_HASH


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


def test_registration_response_does_not_disclose_account_membership() -> None:
    first = client.post(
        "/auth/register",
        json={"email": "member@example.com", "password": "StrongPass123!"},
    )
    second = client.post(
        "/auth/register",
        json={"email": "member@example.com", "password": "DifferentPass123!"},
    )

    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert first.json() == {"message": auth_api.REGISTRATION_RESPONSE_MESSAGE}

    db = SessionLocal()
    try:
        assert db.query(User).filter(User.email == "member@example.com").count() == 1
        assert db.query(AuditLog).filter(AuditLog.event_type == "ACCOUNT_CREATED").count() == 1
    finally:
        db.close()
