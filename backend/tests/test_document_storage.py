import os
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
    LocalDocumentStorage,
)


@pytest.fixture()
def storage(tmp_path) -> LocalDocumentStorage:
    return LocalDocumentStorage(root=tmp_path / "documents")


def test_base_storage_methods_are_abstract() -> None:
    base = DocumentStorage()
    document_id = str(uuid.uuid4())
    for call in (
        lambda: base.save_encrypted(document_id, b"data"),
        lambda: base.read_encrypted(document_id),
        lambda: base.exists(document_id),
        lambda: base.archive(document_id),
        lambda: base.delete_permanently(document_id),
    ):
        with pytest.raises(NotImplementedError):
            call()


def test_init_creates_active_and_archive_roots(storage) -> None:
    assert storage.active_root.is_dir()
    assert storage.archive_root.is_dir()


def test_save_and_read_round_trip(storage) -> None:
    document_id = str(uuid.uuid4())
    relative = storage.save_encrypted(document_id, b"cipher-bytes")

    assert relative.startswith("active")
    assert storage.exists(document_id) is True
    assert storage.read_encrypted(document_id) == b"cipher-bytes"


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
