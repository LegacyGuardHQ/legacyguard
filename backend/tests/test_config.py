import os
from unittest.mock import patch

import pytest

from app.config import DEV_ENCRYPTION_KEY, Settings


EXPLICIT_ENCRYPTION_KEY = "YmJiYmJiYmJiYmJiYmJiYmJiYmJiYmJiYmJiYmJiYmI="


def test_production_requires_strong_secret_keys() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "DATABASE_URL": "sqlite:///./legacyguard.db",
            "SECRET_KEY": "short",
            "ENCRYPTION_KEY": EXPLICIT_ENCRYPTION_KEY,
            "JWT_SECRET": "short",
            "CORS_ALLOWED_ORIGINS": "https://example.com",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="secret_key must be at least 24 characters"):
            Settings()


def test_production_rejects_default_encryption_key() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "DATABASE_URL": "sqlite:///./legacyguard.db",
            "SECRET_KEY": "a-very-long-production-secret-123",
            "ENCRYPTION_KEY": "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
            "JWT_SECRET": "a-very-long-production-jwt-secret-123",
            "CORS_ALLOWED_ORIGINS": "https://example.com",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="encryption_key must be explicitly configured outside testing"):
            Settings()


def test_production_rejects_wildcard_cors() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "DATABASE_URL": "sqlite:///./legacyguard.db",
            "SECRET_KEY": "a-very-long-production-secret-123",
            "ENCRYPTION_KEY": EXPLICIT_ENCRYPTION_KEY,
            "JWT_SECRET": "a-very-long-production-jwt-secret-123",
            "CORS_ALLOWED_ORIGINS": "*",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="Wildcard CORS origins are not allowed"):
            Settings()


@pytest.mark.parametrize("environment", ["development", "staging"])
def test_non_test_environments_reject_default_cryptographic_keys(environment: str) -> None:
    with patch.dict(os.environ, {"ENVIRONMENT": environment}, clear=True):
        with pytest.raises(ValueError, match="encryption_key must be explicitly configured outside testing"):
            Settings()


def test_development_accepts_explicit_cryptographic_keys() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "development",
            "SECRET_KEY": "explicit-development-secret-123",
            "ENCRYPTION_KEY": EXPLICIT_ENCRYPTION_KEY,
            "JWT_SECRET": "explicit-development-jwt-secret-123",
        },
        clear=True,
    ):
        configured = Settings()

    assert configured.environment == "development"
    assert configured.encryption_key != DEV_ENCRYPTION_KEY


def test_testing_environment_keeps_isolated_test_defaults() -> None:
    with patch.dict(os.environ, {"ENVIRONMENT": "testing"}, clear=True):
        configured = Settings()

    assert configured.environment == "testing"
    assert configured.encryption_key == DEV_ENCRYPTION_KEY
