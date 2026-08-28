import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from app.services.operational_logging import log_event, sanitize_for_logging

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


def test_lifespan_logs_startup_and_shutdown() -> None:
    from app.main import app, lifespan
    from app.services import operational_logging

    class CaptureHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.messages: list[str] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.messages.append(record.getMessage())

    handler = CaptureHandler()
    logger = operational_logging.logger
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        async def run_lifespan() -> None:
            async with lifespan(app):
                return None

        asyncio.run(run_lifespan())
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    messages = "\n".join(handler.messages)
    assert "startup_begin" in messages
    assert "startup_complete" in messages
    assert "shutdown" in messages


def test_ready_check_emits_degraded_health_event_without_sensitive_payload() -> None:
    from app.api.health import ready_check
    from app.services import operational_logging

    class CaptureHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.messages: list[str] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.messages.append(record.getMessage())

    handler = CaptureHandler()
    logger = operational_logging.logger
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        with patch("app.api.health.check_database_ready", return_value=False), patch(
            "app.api.health.check_storage_ready", return_value=False
        ), patch("app.api.health.check_migration_ready", return_value=False):
            response = ready_check()
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    assert response.status_code == 503
    messages = "\n".join(handler.messages)
    assert "ready_check_degraded" in messages
    assert "database" in messages and "storage" in messages and "migrations" in messages
    assert "super-secret" not in messages


def test_auth_failure_logging_redacts_sensitive_fields() -> None:
    from app.services import operational_logging

    class CaptureHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.messages: list[str] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.messages.append(record.getMessage())

    handler = CaptureHandler()
    logger = operational_logging.logger
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        log_event(
            "auth_failure",
            event_category="auth",
            severity="warning",
            reason="invalid_credentials",
            password="super-secret",
            token="abc123",
        )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    messages = "\n".join(handler.messages)
    assert "auth_failure" in messages
    assert "invalid_credentials" in messages
    assert "super-secret" not in messages
    assert "abc123" not in messages
    assert "[REDACTED]" in messages


def test_isolated_deployment_smoke_script_runs() -> None:
    env = os.environ.copy()
    env.update(
        {
            "ENVIRONMENT": "testing",
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
    assert "isolated deployment smoke test passed" in result.stdout.lower()
