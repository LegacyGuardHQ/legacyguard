from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionClosedError,
    EndpointConnectionError,
    ReadTimeoutError,
)

from app.config import Settings
from app.services.document_storage import (
    DocumentIntegrityError,
    DocumentStorage,
    DocumentStorageError,
    StorageReadiness,
    StorageWriteResult,
)

_MISSING_CODES = {"404", "NoSuchKey", "NotFound"}
_PRECONDITION_CODES = {"PreconditionFailed", "412", "ConditionalRequestConflict"}
_LOCATOR_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ObjectDocumentStorage(DocumentStorage):
    backend_name = "OBJECT"

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str,
        region: str | None = None,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        session_token: str | None = None,
        addressing_style: str = "auto",
        connect_timeout_seconds: int = 5,
        read_timeout_seconds: int = 30,
        max_attempts: int = 3,
        client: Any | None = None,
    ) -> None:
        normalized_prefix = prefix.strip("/")
        if not bucket or not normalized_prefix or any(
            part in {"", ".", ".."} or not _LOCATOR_COMPONENT.fullmatch(part)
            for part in normalized_prefix.split("/")
        ):
            raise DocumentStorageError("Object storage bucket or prefix is invalid")
        self.bucket = bucket
        self.prefix = normalized_prefix
        self._locator_prefix = f"{self.prefix}/documents/"
        self.client = client or boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token,
            config=Config(
                connect_timeout=connect_timeout_seconds,
                read_timeout=read_timeout_seconds,
                retries={"mode": "standard", "max_attempts": max_attempts},
                s3={"addressing_style": addressing_style},
                signature_version="s3v4",
            ),
        )

    @classmethod
    def from_settings(cls, configuration: Settings) -> "ObjectDocumentStorage":
        if configuration.document_object_bucket is None:
            raise DocumentStorageError("Object storage configuration is incomplete")
        return cls(
            bucket=configuration.document_object_bucket,
            prefix=configuration.document_object_prefix,
            region=configuration.document_object_region,
            endpoint_url=configuration.document_object_endpoint_url,
            access_key_id=configuration.document_object_access_key_id,
            secret_access_key=configuration.document_object_secret_access_key,
            session_token=configuration.document_object_session_token,
            addressing_style=configuration.document_object_addressing_style,
            connect_timeout_seconds=configuration.document_object_connect_timeout_seconds,
            read_timeout_seconds=configuration.document_object_read_timeout_seconds,
            max_attempts=configuration.document_object_max_attempts,
        )

    def _new_locator(self, document_id: str) -> str:
        try:
            document_uuid = uuid.UUID(document_id)
        except ValueError as exc:
            raise DocumentStorageError("Document id must be an opaque UUID") from exc
        return f"{self._locator_prefix}{document_uuid}/{uuid.uuid4()}.lgdoc"

    def _validated_locator(self, locator: str) -> str:
        if not locator.startswith(self._locator_prefix) or "\\" in locator or "://" in locator:
            raise DocumentStorageError("Invalid object storage locator")
        suffix = locator[len(self._locator_prefix) :]
        parts = suffix.split("/")
        if len(parts) != 2 or any(not part or part in {".", ".."} for part in parts):
            raise DocumentStorageError("Invalid object storage locator")
        try:
            uuid.UUID(parts[0])
            uuid.UUID(parts[1].removesuffix(".lgdoc"))
        except ValueError as exc:
            raise DocumentStorageError("Invalid object storage locator") from exc
        if not parts[1].endswith(".lgdoc") or not all(_LOCATOR_COMPONENT.fullmatch(part) for part in parts):
            raise DocumentStorageError("Invalid object storage locator")
        return locator

    @staticmethod
    def _error_code(exc: ClientError) -> str:
        return str(exc.response.get("Error", {}).get("Code", ""))

    def _head(self, locator: str) -> dict[str, Any]:
        return self.client.head_object(Bucket=self.bucket, Key=locator)

    @staticmethod
    def _head_matches(head: dict[str, Any], *, expected_size: int, expected_sha256: str) -> bool:
        metadata = {str(key).lower(): str(value).lower() for key, value in head.get("Metadata", {}).items()}
        return head.get("ContentLength") == expected_size and hmac.compare_digest(
            metadata.get("legacyguard-sha256", ""),
            expected_sha256,
        )

    def save_encrypted(self, document_id: str, encrypted_bytes: bytes) -> StorageWriteResult:
        if not encrypted_bytes:
            raise DocumentStorageError("Encrypted document bytes are required")
        locator = self._new_locator(document_id)
        checksum_hex = hashlib.sha256(encrypted_bytes).hexdigest()
        response: dict[str, Any] | None = None
        try:
            response = self.client.put_object(
                Bucket=self.bucket,
                Key=locator,
                Body=encrypted_bytes,
                ContentLength=len(encrypted_bytes),
                ContentType="application/octet-stream",
                Metadata={"legacyguard-sha256": checksum_hex},
                IfNoneMatch="*",
            )
        except ClientError as exc:
            if self._error_code(exc) in _PRECONDITION_CODES:
                raise DocumentStorageError("Encrypted document object already exists") from exc
            raise DocumentStorageError("Encrypted document could not be stored") from exc
        except (EndpointConnectionError, ConnectionClosedError, ReadTimeoutError) as exc:
            try:
                head = self._head(locator)
            except (BotoCoreError, ClientError):
                raise DocumentStorageError("Encrypted document storage result is unknown") from exc
            if not self._head_matches(head, expected_size=len(encrypted_bytes), expected_sha256=checksum_hex):
                raise DocumentStorageError("Encrypted document storage result is unknown") from exc
            return StorageWriteResult(locator=locator, provider_version=head.get("VersionId"))
        except BotoCoreError as exc:
            raise DocumentStorageError("Encrypted document could not be stored") from exc

        try:
            head = self._head(locator)
        except (BotoCoreError, ClientError) as exc:
            raise DocumentStorageError("Stored document object could not be verified") from exc
        if not self._head_matches(head, expected_size=len(encrypted_bytes), expected_sha256=checksum_hex):
            raise DocumentIntegrityError("Stored document object verification failed")
        return StorageWriteResult(
            locator=locator,
            provider_version=(response or {}).get("VersionId") or head.get("VersionId"),
        )

    def read_encrypted(
        self,
        locator: str,
        *,
        expected_sha256: str | None = None,
        expected_size: int | None = None,
    ) -> bytes:
        locator = self._validated_locator(locator)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=locator)
            if expected_size is not None and response.get("ContentLength") != expected_size:
                response["Body"].close()
                raise DocumentIntegrityError("Encrypted document size mismatch")
            try:
                encrypted_bytes = response["Body"].read()
            finally:
                response["Body"].close()
        except DocumentIntegrityError:
            raise
        except ClientError as exc:
            if self._error_code(exc) in _MISSING_CODES:
                raise DocumentStorageError("Encrypted document not found") from exc
            raise DocumentStorageError("Encrypted document could not be read") from exc
        except BotoCoreError as exc:
            raise DocumentStorageError("Encrypted document could not be read") from exc
        if expected_size is not None and len(encrypted_bytes) != expected_size:
            raise DocumentIntegrityError("Encrypted document size mismatch")
        if expected_sha256 is not None:
            normalized_expected = expected_sha256.strip().lower()
            actual = hashlib.sha256(encrypted_bytes).hexdigest()
            if len(normalized_expected) != 64 or not hmac.compare_digest(actual, normalized_expected):
                raise DocumentIntegrityError("Encrypted document checksum mismatch")
        return encrypted_bytes

    def exists(self, locator: str) -> bool:
        locator = self._validated_locator(locator)
        try:
            self._head(locator)
            return True
        except ClientError as exc:
            if self._error_code(exc) in _MISSING_CODES:
                return False
            raise DocumentStorageError("Object storage availability check failed") from exc
        except BotoCoreError as exc:
            raise DocumentStorageError("Object storage availability check failed") from exc

    def archive(self, locator: str) -> str:
        return self._validated_locator(locator)

    def delete_permanently(self, locator: str) -> None:
        locator = self._validated_locator(locator)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=locator)
        except (BotoCoreError, ClientError) as exc:
            raise DocumentStorageError("Encrypted document could not be deleted") from exc

    def check_readiness(self) -> StorageReadiness:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return StorageReadiness(configuration_valid=True, reachable=True, write_ready=None)
        except (BotoCoreError, ClientError):
            return StorageReadiness(configuration_valid=True, reachable=False, write_ready=None)
