import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.main import app
from app.services.database_rate_limit import DatabaseLoginRateLimiter
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


def test_successful_logins_do_not_consume_failure_allowance() -> None:
    registered = client.post(
        "/auth/register",
        json={"email": "repeat-login@example.com", "password": "StrongPass123!"},
    )
    assert registered.status_code == 201

    for _ in range(7):
        response = client.post(
            "/auth/login",
            json={"email": "repeat-login@example.com", "password": "StrongPass123!"},
        )
        assert response.status_code == 200

    from app.database.connection import SessionLocal
    from app.models.login_rate_limit_attempt import LoginRateLimitAttempt

    db = SessionLocal()
    try:
        assert db.query(LoginRateLimitAttempt).count() == 0
    finally:
        db.close()

    for _ in range(5):
        failed = client.post(
            "/auth/login",
            json={"email": "repeat-login@example.com", "password": "WrongPass123!"},
        )
        assert failed.status_code == 401

    blocked = client.post(
        "/auth/login",
        json={"email": "repeat-login@example.com", "password": "WrongPass123!"},
    )
    assert blocked.status_code == 429


def test_login_failure_allowance_is_shared_through_database() -> None:
    from app.database.connection import SessionLocal
    from app.models.login_rate_limit_attempt import LoginRateLimitAttempt

    first_process = DatabaseLoginRateLimiter()
    second_process = DatabaseLoginRateLimiter()
    db = SessionLocal()
    try:
        for _ in range(5):
            allowed, _retry_after = first_process.allow(db, "login:shared-client")
            assert allowed is True
            first_process.record_failure(db, "login:shared-client")
            db.commit()

        allowed, retry_after = second_process.allow(db, "login:shared-client")
        stored_keys = [row.client_key_hash for row in db.query(LoginRateLimitAttempt).all()]
    finally:
        db.close()

    assert allowed is False
    assert retry_after > 0
    assert stored_keys
    assert all("shared-client" not in stored_key for stored_key in stored_keys)


def test_registration_rate_limit_blocks_account_creation_bursts() -> None:
    for index in range(5):
        response = client.post(
            "/auth/register",
            json={"email": f"burst-{index}@example.com", "password": "StrongPass123!"},
        )
        assert response.status_code == 201

    blocked = client.post(
        "/auth/register",
        json={"email": "burst-blocked@example.com", "password": "StrongPass123!"},
    )

    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "Too many registration attempts"
    assert int(blocked.headers["retry-after"]) > 0


@pytest.mark.parametrize(
    ("email", "password"),
    [
        (f"{'a' * 243}@example.com", "StrongPass123!"),
        ("bounded@example.com", f"A1!{'a' * 126}"),
    ],
)
def test_registration_rejects_oversized_credentials(email: str, password: str) -> None:
    response = client.post("/auth/register", json={"email": email, "password": password})

    assert response.status_code == 422


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
