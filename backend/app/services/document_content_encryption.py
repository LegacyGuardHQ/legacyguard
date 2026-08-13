from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken

from app.services.encryption import EncryptionOperationError, encryption_service

DOCUMENT_CONTENT_ENCRYPTION_VERSION = "FERNET_DEK_V1"
MAX_DEVELOPMENT_DOCUMENT_BYTES = 20 * 1024 * 1024


class DocumentContentEncryptionError(ValueError):
    pass


@dataclass(frozen=True)
class EncryptedDocumentContent:
    encrypted_bytes: bytes
    encrypted_key_reference: str
    checksum_sha256: str
    content_encryption_version: str = DOCUMENT_CONTENT_ENCRYPTION_VERSION


class DocumentContentEncryptionService:
    def encrypt(self, document_id: str, plaintext: bytes) -> EncryptedDocumentContent:
        if not plaintext:
            raise DocumentContentEncryptionError("Document content is required")
        if len(plaintext) > MAX_DEVELOPMENT_DOCUMENT_BYTES:
            raise DocumentContentEncryptionError("Document exceeds maximum size")
        data_key = Fernet.generate_key()
        fernet = Fernet(data_key)
        encrypted_bytes = fernet.encrypt(plaintext)
        key_material = f"{DOCUMENT_CONTENT_ENCRYPTION_VERSION}:{document_id}:{data_key.decode('utf-8')}"
        return EncryptedDocumentContent(
            encrypted_bytes=encrypted_bytes,
            encrypted_key_reference=encryption_service.encrypt(key_material),
            checksum_sha256=hashlib.sha256(encrypted_bytes).hexdigest(),
        )

    def decrypt(self, document_id: str, encrypted_bytes: bytes, encrypted_key_reference: str) -> bytes:
        try:
            key_material = encryption_service.decrypt(encrypted_key_reference)
        except EncryptionOperationError as exc:
            raise DocumentContentEncryptionError("Document key reference could not be decrypted") from exc

        parts = key_material.split(":", 2)
        if len(parts) != 3:
            raise DocumentContentEncryptionError("Document key reference is malformed")
        version, key_document_id, encoded_key = parts
        if version != DOCUMENT_CONTENT_ENCRYPTION_VERSION or key_document_id != document_id:
            raise DocumentContentEncryptionError("Document key reference does not match document")
        try:
            return Fernet(encoded_key.encode("utf-8")).decrypt(encrypted_bytes)
        except (InvalidToken, ValueError) as exc:
            raise DocumentContentEncryptionError("Document content could not be decrypted") from exc


document_content_encryption_service = DocumentContentEncryptionService()
