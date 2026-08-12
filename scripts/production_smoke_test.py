import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient


def _build_smoke_root() -> Path:
    configured_root = os.environ.get("LEGACYGUARD_SMOKE_ROOT")
    if configured_root:
        temp_root = Path(configured_root).resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        return temp_root

    return Path(tempfile.mkdtemp(prefix="legacyguard-smoke-", dir=tempfile.gettempdir()))


def _build_runtime_environment(temp_root: Path) -> dict[str, str]:
    database_url = f"sqlite:///{(temp_root / 'legacyguard.db').resolve().as_posix()}"
    document_storage_root = (temp_root / "documents").resolve()
    document_storage_root.mkdir(parents=True, exist_ok=True)

    return {
        "DATABASE_URL": database_url,
        "SECRET_KEY": "a-very-long-production-secret-123",
        "ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8"),
        "JWT_SECRET": "a-very-long-production-jwt-secret-123",
        "ENVIRONMENT": "production",
        "CORS_ALLOWED_ORIGINS": "https://example.com",
        "DEBUG": "false",
        "DOCUMENT_STORAGE_ROOT": str(document_storage_root),
        "LEGACYGUARD_SMOKE_ROOT": str(temp_root),
    }


def run() -> None:
    temp_root = _build_smoke_root()
    runtime_environment = _build_runtime_environment(temp_root)
    os.environ.update(runtime_environment)

    from app.services.alembic_readiness import upgrade_database_to_head
    from app.main import app

    upgrade_database_to_head(database_url=runtime_environment["DATABASE_URL"])

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

    if not os.environ.get("LEGACYGUARD_SMOKE_ROOT"):
        shutil.rmtree(temp_root, ignore_errors=True)

    print("smoke test passed")


if __name__ == "__main__":
    run()
