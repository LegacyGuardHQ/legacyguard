import hashlib
import os
import socket
import subprocess
import sys
import time
import uuid

import boto3
import pytest
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.models.document import DOCUMENT_STORAGE_STORED, Document
from app.services.discovery_orchestrator import EncryptedDocumentTextProvider
from app.services.document_content_encryption import document_content_encryption_service
from app.services.document_storage import DocumentIntegrityError, DocumentStorageError
from app.services.document_storage_factory import build_document_storage
from app.services.object_document_storage import ObjectDocumentStorage

BUCKET = "legacyguard-synthetic-test"
PREFIX = "synthetic-tenant"


@pytest.fixture(scope="module")
def moto_endpoint():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "moto.server", "-H", "127.0.0.1", "-p", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    endpoint = f"http://127.0.0.1:{port}"
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name="us-east-1",
        aws_access_key_id="synthetic-access-key",
        aws_secret_access_key="synthetic-secret-key",
        config=Config(s3={"addressing_style": "path"}),
    )
    try:
        for _ in range(50):
            try:
                client.list_buckets()
                break
            except Exception:
                if process.poll() is not None:
                    pytest.fail("Moto S3 server exited before becoming ready")
                time.sleep(0.1)
        else:
            pytest.fail("Moto S3 server did not become ready")
        client.create_bucket(Bucket=BUCKET)
        yield endpoint
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture()
def object_storage(moto_endpoint) -> ObjectDocumentStorage:
    return ObjectDocumentStorage(
        bucket=BUCKET,
        prefix=PREFIX,
        region="us-east-1",
        endpoint_url=moto_endpoint,
        access_key_id="synthetic-access-key",
        secret_access_key="synthetic-secret-key",
        addressing_style="path",
        max_attempts=1,
    )


def test_object_storage_protocol_conformance_round_trip(object_storage) -> None:
    document_id = str(uuid.uuid4())
    content = b"encrypted-object-ciphertext"
    result = object_storage.save_encrypted(document_id, content)

    assert result.locator.startswith(f"{PREFIX}/documents/{document_id}/")
    assert result.provider_version is None
    assert result.locator.endswith(".lgdoc")
    assert document_id != result.locator.rsplit("/", 1)[-1]
    assert object_storage.exists(result.locator)
    assert object_storage.read_encrypted(
        result.locator,
        expected_sha256=hashlib.sha256(content).hexdigest(),
        expected_size=len(content),
    ) == content
    assert object_storage.archive(result.locator) == result.locator
    object_storage.delete_permanently(result.locator)
    assert not object_storage.exists(result.locator)
    object_storage.delete_permanently(result.locator)


def test_object_storage_integrity_missing_and_locator_validation(object_storage) -> None:
    result = object_storage.save_encrypted(str(uuid.uuid4()), b"ciphertext")
    with pytest.raises(DocumentIntegrityError, match="checksum"):
        object_storage.read_encrypted(result.locator, expected_sha256="0" * 64)
    with pytest.raises(DocumentIntegrityError, match="size"):
        object_storage.read_encrypted(result.locator, expected_size=999)
    missing = f"{PREFIX}/documents/{uuid.uuid4()}/{uuid.uuid4()}.lgdoc"
    with pytest.raises(DocumentStorageError, match="not found"):
        object_storage.read_encrypted(missing)
    for invalid in (
        "https://example.invalid/object",
        "other-prefix/documents/id/object.lgdoc",
        f"{PREFIX}/../outside.lgdoc",
        f"{PREFIX}/documents/{uuid.uuid4()}/../outside.lgdoc",
        f"{PREFIX}/documents/not-a-uuid/{uuid.uuid4()}.lgdoc",
    ):
        with pytest.raises(DocumentStorageError, match="Invalid object storage locator"):
            object_storage.exists(invalid)


def test_object_storage_readiness_and_nonexistent_bucket(moto_endpoint, object_storage) -> None:
    readiness = object_storage.check_readiness()
    assert readiness.configuration_valid is True
    assert readiness.reachable is True
    assert readiness.write_ready is None

    unavailable = ObjectDocumentStorage(
        bucket="missing-synthetic-bucket",
        prefix=PREFIX,
        region="us-east-1",
        endpoint_url=moto_endpoint,
        access_key_id="synthetic-access-key",
        secret_access_key="synthetic-secret-key",
        addressing_style="path",
        max_attempts=1,
    )
    assert unavailable.check_readiness().reachable is False
    with pytest.raises(DocumentStorageError, match="could not be stored"):
        unavailable.save_encrypted(str(uuid.uuid4()), b"ciphertext")


def test_object_backed_discovery_uses_exact_locator(object_storage) -> None:
    document_id = str(uuid.uuid4())
    encrypted = document_content_encryption_service.encrypt(document_id, b"retirement account")
    result = object_storage.save_encrypted(document_id, encrypted.encrypted_bytes)
    document = Document(
        id=document_id,
        user_id="synthetic-user",
        document_type="ACCOUNT_STATEMENT",
        document_name="Synthetic statement",
        mime_type="text/plain",
        storage_state=DOCUMENT_STORAGE_STORED,
        encryption_key_reference_encrypted=encrypted.encrypted_key_reference,
        ciphertext_sha256=encrypted.checksum_sha256,
        ciphertext_size=len(encrypted.encrypted_bytes),
    )
    document.set_storage_reference(result.locator)

    assert EncryptedDocumentTextProvider(storage=object_storage).get_text(document) == "retirement account"


class AmbiguousPutClient:
    def __init__(self, *, matching: bool = True) -> None:
        self.object: bytes | None = None
        self.metadata: dict[str, str] = {}
        self.matching = matching

    def put_object(self, **kwargs):
        self.object = kwargs["Body"]
        self.metadata = kwargs["Metadata"]
        raise ReadTimeoutError(endpoint_url="https://synthetic.invalid", error="timeout")

    def head_object(self, **kwargs):
        if self.object is None:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return {
            "ContentLength": len(self.object) + (0 if self.matching else 1),
            "Metadata": self.metadata,
            "VersionId": "synthetic-version",
        }


def test_ambiguous_put_reconciles_exact_key_and_rejects_mismatch() -> None:
    matching = ObjectDocumentStorage(bucket=BUCKET, prefix=PREFIX, client=AmbiguousPutClient())
    result = matching.save_encrypted(str(uuid.uuid4()), b"ciphertext")
    assert result.provider_version == "synthetic-version"

    mismatched = ObjectDocumentStorage(bucket=BUCKET, prefix=PREFIX, client=AmbiguousPutClient(matching=False))
    with pytest.raises(DocumentStorageError, match="result is unknown"):
        mismatched.save_encrypted(str(uuid.uuid4()), b"ciphertext")


def test_provider_errors_are_mapped_without_raw_details() -> None:
    class DeniedClient:
        def head_object(self, **kwargs):
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "secret endpoint detail"}},
                "HeadObject",
            )

    storage = ObjectDocumentStorage(bucket=BUCKET, prefix=PREFIX, client=DeniedClient())
    locator = f"{PREFIX}/documents/{uuid.uuid4()}/{uuid.uuid4()}.lgdoc"
    with pytest.raises(DocumentStorageError, match="availability check failed") as error:
        storage.exists(locator)
    assert "secret endpoint detail" not in str(error.value)


def test_constructor_rejects_unsafe_prefix() -> None:
    with pytest.raises(DocumentStorageError, match="bucket or prefix"):
        ObjectDocumentStorage(bucket=BUCKET, prefix="tenant/../escape", client=object())


def test_factory_selects_object_backend_without_changing_local_default(moto_endpoint) -> None:
    from app.config import Settings
    from app.services.document_storage import LocalDocumentStorage

    local = build_document_storage(Settings(_env_file=None, environment="testing"))
    assert isinstance(local, LocalDocumentStorage)

    configured = Settings(
        _env_file=None,
        environment="testing",
        document_storage_backend="OBJECT",
        document_object_bucket=BUCKET,
        document_object_prefix=PREFIX,
        document_object_region="us-east-1",
        document_object_endpoint_url=moto_endpoint,
        document_object_access_key_id="synthetic-access-key",
        document_object_secret_access_key="synthetic-secret-key",
        document_object_addressing_style="path",
        document_object_max_attempts=1,
    )
    assert isinstance(build_document_storage(configured), ObjectDocumentStorage)


def test_endpoint_outage_fails_closed_without_exposing_endpoint() -> None:
    class OfflineClient:
        def head_bucket(self, **kwargs):
            raise EndpointConnectionError(endpoint_url="https://private-storage.example.invalid")

        def put_object(self, **kwargs):
            raise EndpointConnectionError(endpoint_url="https://private-storage.example.invalid")

        def head_object(self, **kwargs):
            raise EndpointConnectionError(endpoint_url="https://private-storage.example.invalid")

    storage = ObjectDocumentStorage(bucket=BUCKET, prefix=PREFIX, client=OfflineClient())
    assert storage.check_readiness().reachable is False
    with pytest.raises(DocumentStorageError, match="result is unknown") as error:
        storage.save_encrypted(str(uuid.uuid4()), b"ciphertext")
    assert "private-storage" not in str(error.value)


def test_invalid_credentials_and_denied_bucket_fail_readiness_safely() -> None:
    class RejectedClient:
        def head_bucket(self, **kwargs):
            raise ClientError(
                {"Error": {"Code": "InvalidAccessKeyId", "Message": "synthetic credential rejected"}},
                "HeadBucket",
            )

    storage = ObjectDocumentStorage(bucket=BUCKET, prefix=PREFIX, client=RejectedClient())
    readiness = storage.check_readiness()
    assert readiness.configuration_valid is True
    assert readiness.reachable is False
    assert readiness.write_ready is None


def test_create_is_conditional_and_duplicate_key_is_not_overwritten() -> None:
    class DuplicateClient:
        def __init__(self) -> None:
            self.if_none_match = None

        def put_object(self, **kwargs):
            self.if_none_match = kwargs.get("IfNoneMatch")
            raise ClientError({"Error": {"Code": "PreconditionFailed"}}, "PutObject")

    client = DuplicateClient()
    storage = ObjectDocumentStorage(bucket=BUCKET, prefix=PREFIX, client=client)
    with pytest.raises(DocumentStorageError, match="already exists"):
        storage.save_encrypted(str(uuid.uuid4()), b"ciphertext")
    assert client.if_none_match == "*"
