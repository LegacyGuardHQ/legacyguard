import os
from pathlib import Path
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
            Settings(_env_file=None)


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
            Settings(_env_file=None)


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
            Settings(_env_file=None)


@pytest.mark.parametrize("environment", ["development", "staging"])
def test_non_test_environments_reject_default_cryptographic_keys(environment: str) -> None:
    with patch.dict(os.environ, {"ENVIRONMENT": environment}, clear=True):
        with pytest.raises(ValueError, match="encryption_key must be explicitly configured outside testing"):
            Settings(_env_file=None)


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
        configured = Settings(_env_file=None)

    assert configured.environment == "development"
    assert configured.encryption_key != DEV_ENCRYPTION_KEY


def test_testing_environment_keeps_isolated_test_defaults() -> None:
    with patch.dict(os.environ, {"ENVIRONMENT": "testing"}, clear=True):
        configured = Settings(_env_file=None)

    assert configured.environment == "testing"
    assert configured.encryption_key == DEV_ENCRYPTION_KEY
    assert configured.document_master_key_id == "legacy-current-v1"


def test_document_master_key_id_is_a_bounded_non_secret_identifier() -> None:
    with patch.dict(
        os.environ,
        {"ENVIRONMENT": "testing", "DOCUMENT_MASTER_KEY_ID": "invalid key identifier"},
        clear=True,
    ):
        with pytest.raises(ValueError, match="document_master_key_id"):
            Settings(_env_file=None)


def test_database_pool_settings_reject_invalid_limits() -> None:
    with patch.dict(
        os.environ,
        {"ENVIRONMENT": "testing", "DATABASE_POOL_SIZE": "0"},
        clear=True,
    ):
        with pytest.raises(ValueError, match="database_pool_size"):
            Settings(_env_file=None)


def test_object_storage_requires_bucket_and_complete_explicit_credentials() -> None:
    with patch.dict(
        os.environ,
        {"ENVIRONMENT": "testing", "DOCUMENT_STORAGE_BACKEND": "OBJECT"},
        clear=True,
    ):
        with pytest.raises(ValueError, match="document_object_bucket"):
            Settings(_env_file=None)

    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "testing",
            "DOCUMENT_STORAGE_BACKEND": "OBJECT",
            "DOCUMENT_OBJECT_BUCKET": "synthetic-documents",
            "DOCUMENT_OBJECT_ACCESS_KEY_ID": "synthetic-access",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="configured together"):
            Settings(_env_file=None)


def test_object_storage_allows_standard_credential_chain_and_safe_endpoint() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "testing",
            "DOCUMENT_STORAGE_BACKEND": "OBJECT",
            "DOCUMENT_OBJECT_BUCKET": "synthetic-documents",
            "DOCUMENT_OBJECT_PREFIX": "/tenant-a/documents-root/",
            "DOCUMENT_OBJECT_ENDPOINT_URL": "http://127.0.0.1:9000",
        },
        clear=True,
    ):
        configured = Settings(_env_file=None)

    assert configured.document_object_prefix == "tenant-a/documents-root"
    assert configured.document_object_access_key_id is None

    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "testing",
            "DOCUMENT_STORAGE_BACKEND": "OBJECT",
            "DOCUMENT_OBJECT_BUCKET": "synthetic-documents",
            "DOCUMENT_OBJECT_PREFIX": "tenant\\escape",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="safe object-key prefix"):
            Settings(_env_file=None)


def test_object_storage_requires_https_outside_development_and_testing() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "DATABASE_URL": "sqlite:///./legacyguard.db",
            "SECRET_KEY": "synthetic-production-secret-123456",
            "ENCRYPTION_KEY": EXPLICIT_ENCRYPTION_KEY,
            "JWT_SECRET": "synthetic-production-jwt-secret-123456",
            "CORS_ALLOWED_ORIGINS": "https://example.com",
            "DOCUMENT_STORAGE_BACKEND": "OBJECT",
            "DOCUMENT_OBJECT_BUCKET": "synthetic-documents",
            "DOCUMENT_OBJECT_ENDPOINT_URL": "http://storage.example.invalid",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="must use HTTPS"):
            Settings(_env_file=None)


def test_default_dotenv_loading_remains_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "ENVIRONMENT=development",
                "DEBUG=false",
                "SECRET_KEY=synthetic-runtime-secret-123456",
                f"ENCRYPTION_KEY={EXPLICIT_ENCRYPTION_KEY}",
                "JWT_SECRET=synthetic-runtime-jwt-secret-123456",
            ]
        ),
        encoding="utf-8",
    )

    with patch.dict(os.environ, {}, clear=True):
        monkeypatch.chdir(tmp_path)
        configured = Settings()

    assert configured.environment == "development"
    assert configured.encryption_key == EXPLICIT_ENCRYPTION_KEY
