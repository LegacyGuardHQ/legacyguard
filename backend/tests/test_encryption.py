import os

import pytest
from cryptography.fernet import Fernet

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.config import DEV_ENCRYPTION_KEY, Settings
from app.services.encryption import EncryptionConfigurationError, EncryptionOperationError, EncryptionService, validate_encryption_key


def test_encryption_produces_ciphertext_and_decrypts_original_value() -> None:
    service = EncryptionService(Fernet.generate_key().decode("utf-8"))
    plaintext = "account-number-1234"

    ciphertext = service.encrypt(plaintext)

    assert ciphertext != plaintext
    assert plaintext not in ciphertext
    assert service.decrypt(ciphertext) == plaintext


def test_invalid_encryption_key_fails_safely() -> None:
    with pytest.raises(EncryptionConfigurationError, match="valid Fernet key"):
        validate_encryption_key("not-a-fernet-key")


def test_decryption_failure_does_not_return_plaintext() -> None:
    service = EncryptionService(Fernet.generate_key().decode("utf-8"))

    with pytest.raises(EncryptionOperationError, match="Decryption failed"):
        service.decrypt("invalid-ciphertext")


def test_missing_production_encryption_key_fails_configuration() -> None:
    with pytest.raises(ValueError, match="encryption_key is required"):
        Settings(environment="production", encryption_key="")


def test_default_development_encryption_key_is_rejected_in_production() -> None:
    with pytest.raises(ValueError, match="encryption_key must be explicitly configured outside testing"):
        Settings(environment="production", encryption_key=DEV_ENCRYPTION_KEY)
