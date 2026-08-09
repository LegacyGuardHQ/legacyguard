import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from app.services.operational_logging import sanitize_for_logging

ROOT = Path(__file__).resolve().parents[2]
VALID_FERNET_KEY = Fernet.generate_key().decode("utf-8")


def test_sanitize_for_logging_redacts_sensitive_values() -> None:
    payload = {
        "message": "login attempt",
        "password": "super-secret",
        "authorization": "Bearer abc123",
        "nested": {"jwt": "token-value", "safe": "ok"},
    }

    sanitized = sanitize_for_logging(payload)

    assert sanitized["message"] == "login attempt"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["nested"]["jwt"] == "[REDACTED]"
    assert sanitized["nested"]["safe"] == "ok"


def test_lifespan_logs_startup_and_shutdown(caplog: pytest.LogCaptureFixture) -> None:
    from app.main import app

    caplog.set_level(logging.INFO, logger="legacyguard")

    async def run_lifespan() -> None:
        async with app.router.lifespan_context(app):
            return None

    asyncio.run(run_lifespan())

    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "startup_begin" in messages
    assert "startup_complete" in messages
    assert "shutdown" in messages


def test_production_smoke_script_runs() -> None:
    env = os.environ.copy()
    env.update(
        {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "DATABASE_URL": "sqlite:///./legacyguard.db",
            "SECRET_KEY": "a-very-long-production-secret-123",
            "ENCRYPTION_KEY": VALID_FERNET_KEY,
            "JWT_SECRET": "a-very-long-production-jwt-secret-123",
            "CORS_ALLOWED_ORIGINS": "https://example.com",
        }
    )

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "production_smoke_test.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "smoke test passed" in result.stdout.lower()
