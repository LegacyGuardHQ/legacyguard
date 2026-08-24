import os
import hashlib
import uuid

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.services.document_storage import (
    DocumentStorage,
    DocumentStorageError,
    DocumentIntegrityError,
    LocalDocumentStorage,
)


@pytest.fixture()
def storage(tmp_path) -> LocalDocumentStorage:
    return LocalDocumentStorage(root=tmp_path / "documents")


def assert_storage_contract(storage: DocumentStorage) -> None:
    document_id = str(uuid.uuid4())
    content = b"contract-ciphertext"
    locator = storage.save_encrypted(document_id, content)

    assert isinstance(locator, str) and locator
    assert storage.exists(document_id) is True
    assert storage.read_encrypted(document_id) == content
    storage.archive(document_id)
    assert storage.read_encrypted(document_id) == content
    storage.delete_permanently(document_id)
    assert storage.exists(document_id) is False


def test_local_storage_conforms_to_backend_neutral_contract(storage) -> None:
    assert_storage_contract(storage)


def test_base_storage_methods_are_abstract() -> None:
    with pytest.raises(TypeError, match="abstract class"):
        DocumentStorage()


def test_init_creates_active_and_archive_roots(storage) -> None:
    assert storage.active_root.is_dir()
    assert storage.archive_root.is_dir()


def test_save_and_read_round_trip(storage) -> None:
    document_id = str(uuid.uuid4())
    relative = storage.save_encrypted(document_id, b"cipher-bytes")

    assert relative.startswith("active")
    assert storage.exists(document_id) is True
    assert storage.read_encrypted(document_id) == b"cipher-bytes"


def test_read_verifies_ciphertext_hash_and_size(storage) -> None:
    document_id = str(uuid.uuid4())
    content = b"cipher-bytes"
    storage.save_encrypted(document_id, content)

    assert storage.read_encrypted(
        document_id,
        expected_sha256=hashlib.sha256(content).hexdigest().upper(),
        expected_size=len(content),
    ) == content

    with pytest.raises(DocumentIntegrityError, match="checksum"):
        storage.read_encrypted(document_id, expected_sha256="0" * 64)
    with pytest.raises(DocumentIntegrityError, match="size"):
        storage.read_encrypted(document_id, expected_size=len(content) + 1)


def test_failed_atomic_replace_leaves_no_final_or_temporary_file(storage, monkeypatch) -> None:
    document_id = str(uuid.uuid4())

    def fail_replace(source, target):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(DocumentStorageError, match="could not be stored"):
        storage.save_encrypted(document_id, b"cipher-bytes")

    assert storage.exists(document_id) is False
    assert list(storage.active_root.glob(".upload-*.tmp")) == []


def test_readiness_is_non_destructive_and_reports_local_roots(storage) -> None:
    before = set(storage.root.rglob("*"))
    readiness = storage.check_readiness()
    after = set(storage.root.rglob("*"))

    assert readiness.configuration_valid is True
    assert readiness.reachable is True
    assert readiness.write_ready is True
    assert readiness.ready is True
    assert before == after


def test_save_rejects_empty_bytes(storage) -> None:
    document_id = str(uuid.uuid4())
    with pytest.raises(DocumentStorageError, match="required"):
        storage.save_encrypted(document_id, b"")


def test_non_uuid_document_id_is_rejected(storage) -> None:
    with pytest.raises(DocumentStorageError, match="opaque UUID"):
        storage.save_encrypted("../../etc/passwd", b"data")


def test_read_missing_document_raises(storage) -> None:
    with pytest.raises(DocumentStorageError, match="not found"):
        storage.read_encrypted(str(uuid.uuid4()))


def test_exists_is_false_for_unknown_document(storage) -> None:
    assert storage.exists(str(uuid.uuid4())) is False


def test_archive_moves_document_and_read_falls_back_to_archive(storage) -> None:
    document_id = str(uuid.uuid4())
    storage.save_encrypted(document_id, b"cipher-bytes")

    storage.archive(document_id)

    assert storage.exists(document_id) is True
    assert storage.read_encrypted(document_id) == b"cipher-bytes"


def test_archive_missing_document_raises(storage) -> None:
    with pytest.raises(DocumentStorageError, match="not found"):
        storage.archive(str(uuid.uuid4()))


def test_delete_permanently_removes_active_and_archived_copies(storage) -> None:
    document_id = str(uuid.uuid4())
    storage.save_encrypted(document_id, b"cipher-bytes")
    storage.archive(document_id)

    storage.delete_permanently(document_id)

    assert storage.exists(document_id) is False


def test_delete_permanently_is_noop_when_absent(storage) -> None:
    storage.delete_permanently(str(uuid.uuid4()))
    assert True
