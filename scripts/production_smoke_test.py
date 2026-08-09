import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.database.connection import init_db

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "a-very-long-production-secret-123")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))
os.environ.setdefault("JWT_SECRET", "a-very-long-production-jwt-secret-123")
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "https://example.com")
os.environ.setdefault("DEBUG", "false")

from app.main import app


def run() -> None:
    init_db()
    client = TestClient(app)
    live = client.get("/health/live")
    if live.status_code != 200:
        raise SystemExit(f"live probe failed: {live.status_code}")

    ready = client.get("/health/ready")
    if ready.status_code != 200:
        raise SystemExit(f"ready probe failed: {ready.status_code}")

    login = client.post(
        "/auth/login",
        json={"email": "unknown@example.com", "password": "wrong"},
    )
    if login.status_code not in {200, 401, 403, 429}:
        raise SystemExit(f"auth endpoint unexpected status: {login.status_code}")

    print("smoke test passed")


if __name__ == "__main__":
    run()
