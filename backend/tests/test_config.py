import os
from unittest.mock import patch

import pytest

from app.config import Settings


def test_production_requires_strong_secret_keys() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "DATABASE_URL": "sqlite:///./legacyguard.db",
            "SECRET_KEY": "short",
            "ENCRYPTION_KEY": "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
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
        with pytest.raises(ValueError, match="production encryption_key must be explicitly configured"):
            Settings()


def test_production_rejects_wildcard_cors() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "DATABASE_URL": "sqlite:///./legacyguard.db",
            "SECRET_KEY": "a-very-long-production-secret-123",
            "ENCRYPTION_KEY": "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
            "JWT_SECRET": "a-very-long-production-jwt-secret-123",
            "CORS_ALLOWED_ORIGINS": "*",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="Wildcard CORS origins are not allowed"):
            Settings()
