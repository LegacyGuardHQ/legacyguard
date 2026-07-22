from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken

from app.config import settings


class EncryptionConfigurationError(RuntimeError):
    pass


class EncryptionOperationError(RuntimeError):
    pass


def validate_encryption_key(key: str) -> None:
    if not key:
        raise EncryptionConfigurationError("ENCRYPTION_KEY is required")
    try:
        Fernet(key.encode("utf-8"))
    except Exception as exc:
        raise EncryptionConfigurationError("ENCRYPTION_KEY must be a valid Fernet key") from exc


class EncryptionService:
    def __init__(self, key: str | None = None) -> None:
        resolved_key = key or settings.encryption_key
        validate_encryption_key(resolved_key)
        self._fernet = Fernet(resolved_key.encode("utf-8"))

    def encrypt(self, value: str) -> str:
        return encrypt_value(value, self._fernet)

    def decrypt(self, token: str) -> str:
        return decrypt_value(token, self._fernet)


def encrypt_value(value: str, fernet: Fernet | None = None) -> str:
    if value is None:
        raise EncryptionOperationError("Cannot encrypt a null value")
    try:
        cipher = fernet or encryption_service._fernet
        return cipher.encrypt(value.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise EncryptionOperationError("Encryption failed") from exc


def decrypt_value(token: str, fernet: Fernet | None = None) -> str:
    if not token:
        raise EncryptionOperationError("Cannot decrypt an empty value")
    try:
        cipher = fernet or encryption_service._fernet
        return cipher.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionOperationError("Decryption failed") from exc


encryption_service = EncryptionService()
