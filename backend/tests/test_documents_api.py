import asyncio
import hashlib
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.api import documents as documents_api
from app.database.connection import SessionLocal
from app.main import app
from app.models.asset import ASSET_STATUS_ARCHIVED, Asset
from app.models.beneficiary import BENEFICIARY_STATUS_ARCHIVED, Beneficiary
from app.models.audit_log import AuditLog
from app.models.discovery import (
    DISCOVERY_SCAN_STATUS_COMPLETE,
    DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS,
    DISCOVERY_SCAN_STATUS_FAILED,
    DISCOVERY_SCAN_STATUS_PENDING,
    DISCOVERY_SCAN_STATUS_RUNNING,
    DiscoveryScan,
    EvidenceFinding,
)
from app.models.discovery_scan_document import (
    DISCOVERY_DOCUMENT_STATUS_FAILED,
    DISCOVERY_DOCUMENT_STATUS_SKIPPED,
    DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED,
    DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION,
    DiscoveryScanDocument,
)
from app.models.document import Document
from app.services.discovery_orchestrator import DISCOVERY_FAILED, DiscoveryOrchestrator, EncryptedDocumentTextProvider
from app.services.document_storage import DocumentIntegrityError
from app.services.document_validation import DocumentValidationError, MAX_DOCUMENT_BYTES
from app.services.rate_limit import rate_limiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    from app.database.connection import Base, engine

    rate_limiter.reset_all()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    rate_limiter.reset_all()


def _token(email: str) -> str:
    password = "StrongPass123!"
    assert client.post("/auth/register", json={"email": email, "password": password}).status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def _create_asset(token: str, name: str = "Checking") -> dict:
    response = client.post(
        "/assets",
        headers={"Authorization": f"Bearer {token}"},
        json={"asset_name": name, "asset_category": "Bank Account", "estimated_value": "1000.00"},
    )
    assert response.status_code == 201
    return response.json()


def _create_beneficiary(token: str, name: str = "Jane Doe") -> dict:
    response = client.post(
        "/beneficiaries",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "relationship_type": "Spouse", "contact_information": "private@example.com", "notes": "Sensitive note"},
    )
    assert response.status_code == 201
    return response.json()


def _post_document(token: str, **overrides):
    payload = {
        "document_type": "WILL",
        "document_name": "Estate Will",
        "description": "Sensitive description",
        "original_filename": "will.pdf",
        "mime_type": "application/pdf",
        "file_size": 1024,
        "version_number": 1,
    }
    payload.update(overrides)
    return client.post("/documents", headers={"Authorization": f"Bearer {token}"}, json=payload)


def _storage_locator(document_id: str) -> str:
    db = SessionLocal()
    try:
        locator = db.query(Document).filter(Document.id == document_id).one().get_storage_reference()
        assert locator is not None
        return locator
    finally:
        db.close()


class OpaqueMemoryStorage:
    locator = "opaque/random/upload-attempt-a9f7.lgdoc"

    def __init__(self) -> None:
        self.blobs: dict[str, bytes] = {}

    def save_encrypted(self, document_id: str, encrypted_bytes: bytes) -> str:
        assert document_id not in self.locator
        self.blobs[self.locator] = encrypted_bytes
        return self.locator

    def read_encrypted(self, locator: str, *, expected_sha256=None, expected_size=None) -> bytes:
        encrypted_bytes = self.blobs[locator]
        if expected_size is not None and len(encrypted_bytes) != expected_size:
            raise DocumentIntegrityError("Encrypted document size mismatch")
        if expected_sha256 is not None and hashlib.sha256(encrypted_bytes).hexdigest() != expected_sha256:
            raise DocumentIntegrityError("Encrypted document checksum mismatch")
        return encrypted_bytes

    def exists(self, locator: str) -> bool:
        return locator in self.blobs

    def archive(self, locator: str) -> str:
        archived_locator = f"archived/{locator}"
        self.blobs[archived_locator] = self.blobs.pop(locator)
        return archived_locator

    def delete_permanently(self, locator: str) -> None:
        self.blobs.pop(locator, None)


def test_authenticated_user_creates_metadata_only_document_and_user_id_server_side() -> None:
    token = _token("owner@example.com")

    response = _post_document(token, user_id="malicious-user")

    assert response.status_code == 422

    response = _post_document(token)
    assert response.status_code == 201
    payload = response.json()
    assert payload["document_type"] == "WILL"
    assert payload["document_name"] == "Estate Will"
    assert payload["description"] == "Sensitive description"
    assert payload["status"] == "ACTIVE"
    assert payload["verification_status"] == "UNKNOWN"
    assert payload["verified_at"] is None
    assert payload["archived_at"] is None
    assert "user_id" not in payload

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == payload["id"]).one()
        assert document.user_id != "malicious-user"
        assert document.storage_reference is None
        assert document.storage_reference_encrypted is None
        assert document.encryption_key_reference_encrypted is None
        assert document.checksum_sha256 is None
    finally:
        db.close()


def test_user_lists_only_own_documents() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    owner_doc = _post_document(owner_token, document_name="Owner Doc")
    other_doc = _post_document(other_token, document_name="Other Doc")
    assert owner_doc.status_code == 201
    assert other_doc.status_code == 201

    response = client.get("/documents", headers={"Authorization": f"Bearer {owner_token}"})

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [owner_doc.json()["id"]]
    assert payload[0]["document_name"] == "Owner Doc"


def test_cross_user_detail_access_returns_404() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    document = _post_document(owner_token)
    assert document.status_code == 201

    response = client.get(f"/documents/{document.json()['id']}", headers={"Authorization": f"Bearer {other_token}"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_cross_user_asset_and_beneficiary_linkage_blocked() -> None:
    owner_token = _token("owner@example.com")
    other_token = _token("other@example.com")
    other_asset = _create_asset(other_token)
    other_beneficiary = _create_beneficiary(other_token)

    asset_response = _post_document(owner_token, asset_id=other_asset["id"])
    beneficiary_response = _post_document(owner_token, beneficiary_id=other_beneficiary["id"])

    assert asset_response.status_code == 404
    assert beneficiary_response.status_code == 404


def test_document_can_link_to_owned_asset_beneficiary_both_or_neither() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)

    neither = _post_document(token, document_name="Neither")
    asset_only = _post_document(token, document_name="Asset", asset_id=asset["id"])
    beneficiary_only = _post_document(token, document_name="Beneficiary", beneficiary_id=beneficiary["id"])
    both = _post_document(token, document_name="Both", asset_id=asset["id"], beneficiary_id=beneficiary["id"])

    assert neither.status_code == 201
    assert asset_only.status_code == 201
    assert beneficiary_only.status_code == 201
    assert both.status_code == 201
    assert both.json()["asset_id"] == asset["id"]
    assert both.json()["beneficiary_id"] == beneficiary["id"]


def test_description_encrypted_in_storage_and_detail_decrypts_after_ownership() -> None:
    token = _token("owner@example.com")
    response = _post_document(token, description="Private vault note")
    assert response.status_code == 201
    document_id = response.json()["id"]

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).one()
        assert document.description_encrypted != "Private vault note"
        assert document.get_description() == "Private vault note"
    finally:
        db.close()

    detail = client.get(f"/documents/{document_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail.status_code == 200
    assert detail.json()["description"] == "Private vault note"


def test_list_response_excludes_sensitive_fields() -> None:
    token = _token("owner@example.com")
    assert _post_document(token).status_code == 201

    response = client.get("/documents", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    item = response.json()[0]
    for field in (
        "storage_reference",
        "storage_reference_encrypted",
        "encryption_key_reference_encrypted",
        "ciphertext",
        "description",
        "user_id",
        "checksum_sha256",
    ):
        assert field not in item


def test_client_cannot_provide_storage_or_key_reference_or_checksum() -> None:
    token = _token("owner@example.com")

    for forbidden in ("storage_reference", "storage_reference_encrypted", "encryption_key_reference_encrypted", "checksum_sha256"):
        response = _post_document(token, **{forbidden: "client-supplied"})
        assert response.status_code == 422


def test_invalid_document_type_and_filename_mime_rejected() -> None:
    token = _token("owner@example.com")

    invalid_type = _post_document(token, document_type="RANDOM")
    invalid_combo = _post_document(token, original_filename="will.pdf", mime_type="image/png")

    assert invalid_type.status_code == 422
    assert invalid_combo.status_code == 422


def test_archived_linked_asset_or_beneficiary_rejected() -> None:
    token = _token("owner@example.com")
    asset = _create_asset(token)
    beneficiary = _create_beneficiary(token)

    db = SessionLocal()
    try:
        db_asset = db.query(Asset).filter(Asset.id == asset["id"]).one()
        db_asset.status = ASSET_STATUS_ARCHIVED
        db_beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary["id"]).one()
        db_beneficiary.status = BENEFICIARY_STATUS_ARCHIVED
        db.commit()
    finally:
        db.close()

    asset_response = _post_document(token, asset_id=asset["id"])
    beneficiary_response = _post_document(token, beneficiary_id=beneficiary["id"])

    assert asset_response.status_code == 400
    assert "Archived assets" in asset_response.json()["detail"]
    assert beneficiary_response.status_code == 400
    assert "Archived beneficiaries" in beneficiary_response.json()["detail"]


def test_unauthenticated_document_requests_rejected() -> None:
    create_response = client.post("/documents", json={"document_type": "WILL", "document_name": "Will"})
    list_response = client.get("/documents")
    detail_response = client.get("/documents/doc-id")

    assert create_response.status_code in (401, 403)
    assert list_response.status_code in (401, 403)
    assert detail_response.status_code in (401, 403)


def _upload_document(token: str, document_id: str, content: bytes = b"%PDF-1.4\n%test pdf\n", filename: str = "upload.pdf", mime_type: str = "application/pdf", **fields):
    data = {key: value for key, value in fields.items()}
    return client.post(
        f"/documents/{document_id}/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, content, mime_type)},
        data=data,
    )


def test_upload_storage_builder_uses_configured_root(monkeypatch, tmp_path) -> None:
    configured_root = tmp_path / "configured-upload-storage"
    monkeypatch.setattr(documents_api.settings, "document_storage_root", str(configured_root))

    storage = documents_api._build_document_storage()

    assert storage.root == configured_root.resolve()


def test_upload_reader_enforces_limit_without_unbounded_read() -> None:
    class OversizedUpload:
        def __init__(self) -> None:
            self.remaining = MAX_DOCUMENT_BYTES + 1
            self.requested_sizes: list[int] = []

        async def read(self, size: int) -> bytes:
            self.requested_sizes.append(size)
            returned = min(size, self.remaining)
            self.remaining -= returned
            return b"x" * returned

    upload = OversizedUpload()

    with pytest.raises(DocumentValidationError, match="Document exceeds maximum size"):
        asyncio.run(documents_api._read_bounded_upload(upload))

    assert upload.requested_sizes
    assert max(upload.requested_sizes) == documents_api.UPLOAD_READ_CHUNK_BYTES
    assert all(size > 0 for size in upload.requested_sizes)


def test_owner_uploads_valid_pdf_and_response_is_private() -> None:
    token = _token("upload-owner@example.com")
    document = _post_document(token, original_filename="old.txt", mime_type="text/plain", file_size=1)
    assert document.status_code == 201
    document_id = document.json()["id"]
    plaintext = b"%PDF-1.4\nvalid pdf bytes"

    response = _upload_document(token, document_id, content=plaintext)

    assert response.status_code == 200
    assert "checksum_sha256" not in response.json()
    payload = response.json()
    assert payload["id"] == document_id
    assert payload["original_filename"] == "upload.pdf"
    assert payload["mime_type"] == "application/pdf"
    assert payload["file_size"] == len(plaintext)
    assert payload["upload_status"] == "COMPLETED"
    for field in ("storage_reference", "storage_reference_encrypted", "key_reference", "encryption_key_reference_encrypted", "ciphertext", "filesystem_path"):
        assert field not in payload


def test_upload_rejects_unauthenticated_cross_user_and_archived_document() -> None:
    owner_token = _token("upload-owner@example.com")
    other_token = _token("upload-other@example.com")
    document = _post_document(owner_token)
    assert document.status_code == 201
    document_id = document.json()["id"]

    unauth = client.post(f"/documents/{document_id}/upload", files={"file": ("upload.pdf", b"%PDF-1.4", "application/pdf")})
    cross_user = _upload_document(other_token, document_id)

    db = SessionLocal()
    try:
        db_doc = db.query(Document).filter(Document.id == document_id).one()
        db_doc.archived_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()
    archived = _upload_document(owner_token, document_id)

    assert unauth.status_code in (401, 403)
    assert cross_user.status_code == 404
    assert archived.status_code == 400


def test_upload_rejects_empty_oversized_invalid_extension_mismatch_and_path_traversal() -> None:
    token = _token("upload-validation@example.com")
    responses = []
    for kwargs in (
        {"content": b"", "filename": "empty.pdf", "mime_type": "application/pdf"},
        {"content": b"x" * (20 * 1024 * 1024 + 1), "filename": "large.pdf", "mime_type": "application/pdf"},
        {"content": b"not executable", "filename": "bad.exe", "mime_type": "application/pdf"},
        {"content": b"%PDF-1.4", "filename": "bad.pdf", "mime_type": "image/png"},
        {"content": b"%PDF-1.4", "filename": "bad.pdf.exe", "mime_type": "application/pdf"},
        {"content": b"%PDF-1.4", "filename": "../bad.pdf", "mime_type": "application/pdf"},
    ):
        document = _post_document(token)
        assert document.status_code == 201
        responses.append(_upload_document(token, document.json()["id"], **kwargs))

    assert all(response.status_code == 422 for response in responses)


def test_upload_stores_encrypted_bytes_and_recoverable_plaintext() -> None:
    from app.api import documents as documents_api
    from app.services.document_content_encryption import document_content_encryption_service

    token = _token("upload-encrypt@example.com")
    document = _post_document(token)
    plaintext = b"%PDF-1.4\nsecret upload bytes"
    assert document.status_code == 201
    document_id = document.json()["id"]

    response = _upload_document(token, document_id, content=plaintext)

    assert response.status_code == 200
    db = SessionLocal()
    try:
        saved = db.query(Document).filter(Document.id == document_id).one()
        locator = saved.get_storage_reference()
        assert locator is not None
        encrypted_bytes = documents_api.document_storage.read_encrypted(locator)
        assert encrypted_bytes != plaintext
        assert plaintext not in encrypted_bytes
        assert saved.storage_reference is None
        assert saved.storage_reference_encrypted is not None
        assert saved.get_storage_reference() is not None
        assert saved.encryption_key_reference_encrypted is not None
        assert saved.encryption_key_reference_encrypted != "client-key"
        assert document_content_encryption_service.decrypt(document_id, encrypted_bytes, saved.encryption_key_reference_encrypted) == plaintext
        assert saved.checksum_sha256 is None
        assert saved.ciphertext_sha256 == __import__("hashlib").sha256(encrypted_bytes).hexdigest()
        assert saved.ciphertext_size == len(encrypted_bytes)
        assert saved.storage_state == "STORED"
        assert saved.upload_attempt_id is not None
        assert saved.master_key_id == "legacy-current-v1"
    finally:
        db.close()
        documents_api.document_storage.delete_permanently(_storage_locator(document_id))


def test_upload_and_discovery_use_non_derivable_authoritative_locator(monkeypatch) -> None:
    storage = OpaqueMemoryStorage()
    monkeypatch.setattr(documents_api, "document_storage", storage)
    monkeypatch.setattr(documents_api, "_trigger_discovery_scan_after_upload", lambda *args, **kwargs: None)
    token = _token("opaque-storage@example.com")
    document_id = _post_document(
        token,
        original_filename="statement.txt",
        mime_type="text/plain",
        file_size=7,
    ).json()["id"]

    response = _upload_document(
        token,
        document_id,
        content=b"account",
        filename="statement.txt",
        mime_type="text/plain",
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).one()
        locator = document.get_storage_reference()
        assert locator == storage.locator
        assert storage.exists(locator)
        assert EncryptedDocumentTextProvider(storage=storage).get_text(document) == "account"

        wrong_blob = storage.blobs[locator]
        storage.blobs[locator] = b"x" + wrong_blob[1:]
        with pytest.raises(DocumentIntegrityError):
            EncryptedDocumentTextProvider(storage=storage).get_text(document)
        storage.blobs[locator] = wrong_blob

        archived_locator = storage.archive(locator)
        assert storage.exists(archived_locator)
        storage.delete_permanently(archived_locator)
        assert not storage.exists(archived_locator)
    finally:
        db.close()


def test_upload_rejects_client_supplied_extra_fields_and_reupload_conflict() -> None:
    token = _token("upload-conflict@example.com")
    document = _post_document(token)
    assert document.status_code == 201
    document_id = document.json()["id"]

    supplied = _upload_document(token, document_id, storage_reference="x", checksum_sha256="bad", encryption_key_reference="key")
    first = _upload_document(token, document_id)
    second = _upload_document(token, document_id)

    assert supplied.status_code == 200
    assert first.status_code == 409
    assert second.status_code == 409


def test_database_claim_prevents_two_stale_sessions_from_uploading_same_document() -> None:
    from app.api.documents import _claim_upload_attempt

    token = _token("upload-claim-race@example.com")
    document_id = _post_document(token).json()["id"]
    first_db = SessionLocal()
    second_db = SessionLocal()
    try:
        first_document = first_db.query(Document).filter(Document.id == document_id).one()
        second_document = second_db.query(Document).filter(Document.id == document_id).one()

        attempt_id = _claim_upload_attempt(first_db, first_document)
        with pytest.raises(HTTPException) as conflict:
            _claim_upload_attempt(second_db, second_document)

        assert conflict.value.status_code == 409
        assert first_db.query(Document).filter(Document.id == document_id).one().upload_attempt_id == attempt_id
    finally:
        first_db.close()
        second_db.close()


def test_upload_storage_failure_does_not_commit_metadata(monkeypatch) -> None:
    from app.api import documents as documents_api
    from app.services.document_storage import DocumentStorageError

    token = _token("upload-storage-fail@example.com")
    document = _post_document(token)
    document_id = document.json()["id"]

    def fail_save(document_id: str, encrypted_bytes: bytes) -> str:
        raise DocumentStorageError("boom")

    monkeypatch.setattr(documents_api.document_storage, "save_encrypted", fail_save)
    response = _upload_document(token, document_id)

    assert response.status_code == 500
    db = SessionLocal()
    try:
        saved = db.query(Document).filter(Document.id == document_id).one()
        assert saved.storage_reference_encrypted is None
        assert saved.encryption_key_reference_encrypted is None
        assert saved.checksum_sha256 is None
        assert saved.storage_state == "FAILED"
        assert saved.storage_error_code == "STORAGE_WRITE_FAILED"
        assert saved.upload_attempt_id is not None
    finally:
        db.close()


def test_upload_database_failure_after_storage_triggers_cleanup(monkeypatch) -> None:
    from app.api import documents as documents_api

    token = _token("upload-db-fail@example.com")
    document = _post_document(token)
    document_id = document.json()["id"]
    deleted = {"called": False}

    original_commit = SessionLocal().__class__.commit

    def fail_commit(self):
        if getattr(self, "_fail_upload_commit", False):
            raise RuntimeError("db fail")
        return original_commit(self)

    def mark_then_fail(db_self):
        db_self._fail_upload_commit = True
        return fail_commit(db_self)

    monkeypatch.setattr(type(SessionLocal()), "commit", fail_commit, raising=False)

    original_save = documents_api.document_storage.save_encrypted
    original_delete = documents_api.document_storage.delete_permanently

    def save_and_mark(document_id: str, encrypted_bytes: bytes) -> str:
        return original_save(document_id, encrypted_bytes)

    def delete_and_track(locator: str) -> None:
        deleted["called"] = True
        original_delete(locator)

    monkeypatch.setattr(documents_api.document_storage, "save_encrypted", save_and_mark)
    monkeypatch.setattr(documents_api.document_storage, "delete_permanently", delete_and_track)

    # The upload claim commits first; fail the following metadata commit and
    # allow the failure-state commit to succeed.
    commit_calls = {"count": 0}

    def fail_upload_metadata_commit(self):
        commit_calls["count"] += 1
        if commit_calls["count"] == 2:
            raise RuntimeError("db fail")
        return original_commit(self)

    monkeypatch.setattr(type(SessionLocal()), "commit", fail_upload_metadata_commit, raising=False)
    response = _upload_document(token, document_id)

    assert response.status_code == 500
    assert deleted["called"] is True
    db = SessionLocal()
    try:
        saved = db.query(Document).filter(Document.id == document_id).one()
        assert saved.storage_state == "FAILED"
        assert saved.storage_error_code == "DATABASE_COMMIT_FAILED"
        assert saved.storage_reference_encrypted is None
    finally:
        db.close()


def test_upload_triggers_discovery_scan_for_text_document() -> None:
    token = _token("upload-discovery@example.com")
    document = _post_document(token, original_filename="statement.txt", mime_type="text/plain", file_size=32)
    assert document.status_code == 201
    document_id = document.json()["id"]
    plaintext = b"retirement rollover account"

    try:
        response = _upload_document(
            token,
            document_id,
            content=plaintext,
            filename="statement.txt",
            mime_type="text/plain",
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["upload_status"] == "COMPLETED"
        assert payload["discovery_scan"] is not None
        assert payload["discovery_scan"]["status"] == DISCOVERY_SCAN_STATUS_PENDING
        scan_id = payload["discovery_scan"]["scan_id"]

        db = SessionLocal()
        try:
            scan = db.query(DiscoveryScan).filter(DiscoveryScan.id == scan_id).one()
            assert scan.user_id == client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]
            assert scan.status == DISCOVERY_SCAN_STATUS_COMPLETE
            assert scan.documents_processed == 1
            assert db.query(DiscoveryScan).count() == 1
            findings = db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == scan_id).all()
            assert len(findings) >= 1
            assert findings[0].document_id == document_id
            tracking = db.query(DiscoveryScanDocument).filter(DiscoveryScanDocument.scan_id == scan_id).one()
            assert tracking.document_id == document_id
        finally:
            db.close()

        findings_response = client.get(
            f"/discovery/scans/{scan_id}/findings",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert findings_response.status_code == 200
        assert findings_response.json()["total_count"] >= 1
    finally:
        documents_api.document_storage.delete_permanently(_storage_locator(document_id))


def test_upload_still_succeeds_when_discovery_extraction_unsupported() -> None:
    token = _token("upload-discovery-pdf@example.com")
    document = _post_document(token)
    assert document.status_code == 201
    document_id = document.json()["id"]
    plaintext = b"%PDF-1.4\nvalid pdf bytes"

    try:
        response = _upload_document(token, document_id, content=plaintext)

        assert response.status_code == 200
        payload = response.json()
        assert payload["upload_status"] == "COMPLETED"
        assert payload["discovery_scan"] is not None
        assert payload["discovery_scan"]["status"] == DISCOVERY_SCAN_STATUS_PENDING

        db = SessionLocal()
        try:
            saved = db.query(Document).filter(Document.id == document_id).one()
            assert saved.encryption_key_reference_encrypted is not None
            scan = db.query(DiscoveryScan).filter(DiscoveryScan.id == payload["discovery_scan"]["scan_id"]).one()
            assert scan.status == DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS
            assert scan.documents_processed == 0
            tracking = db.query(DiscoveryScanDocument).filter(DiscoveryScanDocument.scan_id == scan.id).one()
            assert tracking.status == DISCOVERY_DOCUMENT_STATUS_SKIPPED
            assert tracking.warning_code == DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION
        finally:
            db.close()

        assert documents_api.document_storage.exists(_storage_locator(document_id))
    finally:
        documents_api.document_storage.delete_permanently(_storage_locator(document_id))


def test_upload_schedules_discovery_without_running_it_inline(monkeypatch) -> None:
    token = _token("upload-discovery-scheduled@example.com")
    document = _post_document(token, original_filename="statement.txt", mime_type="text/plain", file_size=32)
    assert document.status_code == 201
    document_id = document.json()["id"]
    scheduled: dict[str, object] = {}

    def capture_task(self, func, *args, **kwargs):
        scheduled.update({"func": func, "args": args, "kwargs": kwargs})

    def fail_if_processed(*args, **kwargs):
        raise AssertionError("discovery processing ran in the upload response path")

    monkeypatch.setattr(BackgroundTasks, "add_task", capture_task)
    monkeypatch.setattr(documents_api.discovery_scan_executor, "process_existing", fail_if_processed)

    try:
        response = _upload_document(
            token,
            document_id,
            content=b"retirement rollover account",
            filename="statement.txt",
            mime_type="text/plain",
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["upload_status"] == "COMPLETED"
        assert payload["discovery_scan"]["status"] == DISCOVERY_SCAN_STATUS_PENDING
        assert scheduled["func"] is documents_api._process_discovery_scan_in_background
        assert scheduled["args"] == (
            payload["discovery_scan"]["scan_id"],
            client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"],
            document_id,
        )
        assert scheduled["kwargs"] == {}

        db = SessionLocal()
        try:
            saved = db.query(Document).filter(Document.id == document_id).one()
            assert saved.encryption_key_reference_encrypted is not None
            scan = db.query(DiscoveryScan).filter(DiscoveryScan.id == payload["discovery_scan"]["scan_id"]).one()
            assert scan.status == DISCOVERY_SCAN_STATUS_PENDING
            assert db.query(DiscoveryScanDocument).filter(DiscoveryScanDocument.scan_id == scan.id).count() == 0
        finally:
            db.close()
        assert documents_api.document_storage.exists(_storage_locator(document_id))
    finally:
        documents_api.document_storage.delete_permanently(_storage_locator(document_id))


def test_background_discovery_uses_and_closes_fresh_session(monkeypatch) -> None:
    request_session = object()

    class TrackingSession:
        def __init__(self) -> None:
            self.closed = False
            self.rolled_back = False

        def close(self) -> None:
            self.closed = True

        def rollback(self) -> None:
            self.rolled_back = True

    background_session = TrackingSession()
    processed: dict[str, object] = {}

    monkeypatch.setattr(documents_api, "SessionLocal", lambda: background_session)

    def process_existing(db, *, scan_id, user_id, document_ids):
        processed.update(
            {
                "db": db,
                "scan_id": scan_id,
                "user_id": user_id,
                "document_ids": document_ids,
            }
        )

    monkeypatch.setattr(documents_api.discovery_scan_executor, "process_existing", process_existing)

    documents_api._process_discovery_scan_in_background("scan-1", "user-1", "document-1")

    assert processed == {
        "db": background_session,
        "scan_id": "scan-1",
        "user_id": "user-1",
        "document_ids": ["document-1"],
    }
    assert processed["db"] is not request_session
    assert background_session.closed is True
    assert background_session.rolled_back is False


def test_losing_duplicate_background_invocation_does_not_fail_running_scan() -> None:
    token = _token("duplicate-background-discovery@example.com")
    document = _post_document(token, original_filename="statement.txt", mime_type="text/plain", file_size=32)
    assert document.status_code == 201
    document_id = document.json()["id"]
    user_id = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]

    db = SessionLocal()
    try:
        scan = documents_api.discovery_scan_executor.create_pending(db, user_id=user_id)
        scan_id = scan.id
        claimed_rows = (
            db.query(DiscoveryScan)
            .filter(
                DiscoveryScan.id == scan_id,
                DiscoveryScan.user_id == user_id,
                DiscoveryScan.status == DISCOVERY_SCAN_STATUS_PENDING,
            )
            .update(
                {
                    DiscoveryScan.status: DISCOVERY_SCAN_STATUS_RUNNING,
                    DiscoveryScan.started_at: datetime.now(timezone.utc),
                },
                synchronize_session=False,
            )
        )
        db.commit()
        assert claimed_rows == 1
        failure_audits_before = db.query(AuditLog).filter(AuditLog.event_type == DISCOVERY_FAILED).count()
    finally:
        db.close()

    documents_api._process_discovery_scan_in_background(scan_id, user_id, document_id)

    verification_db = SessionLocal()
    try:
        persisted_scan = verification_db.query(DiscoveryScan).filter(DiscoveryScan.id == scan_id).one()
        assert persisted_scan.status == DISCOVERY_SCAN_STATUS_RUNNING
        assert verification_db.query(DiscoveryScanDocument).filter(DiscoveryScanDocument.scan_id == scan_id).count() == 0
        assert verification_db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == scan_id).count() == 0
        assert verification_db.query(AuditLog).filter(AuditLog.event_type == DISCOVERY_FAILED).count() == failure_audits_before
    finally:
        verification_db.close()


def test_background_discovery_recovers_stale_running_scan_without_duplicate_artifacts(monkeypatch) -> None:
    token = _token("stale-background-discovery@example.com")
    document = _post_document(token, original_filename="statement.txt", mime_type="text/plain", file_size=32)
    assert document.status_code == 201
    document_id = document.json()["id"]
    user_id = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]

    db = SessionLocal()
    try:
        scan = documents_api.discovery_scan_executor.create_pending(db, user_id=user_id)
        scan_id = scan.id
        scan.status = DISCOVERY_SCAN_STATUS_RUNNING
        scan.started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        stale_tracking = DiscoveryScanDocument(
            id="tracking-old",
            scan_id=scan_id,
            document_id=document_id,
            status=DISCOVERY_DOCUMENT_STATUS_FAILED,
        )
        stale_finding = EvidenceFinding(
            id="finding-old",
            scan_id=scan_id,
            document_id=document_id,
            category="OLD_CATEGORY",
            confidence_score=99.0,
        )
        db.add_all([stale_tracking, stale_finding])
        db.commit()
    finally:
        db.close()

    class StubTextProvider:
        def get_text(self, document):
            return "retirement rollover"

    class StubDiscoveryEngine:
        def analyze_text(self, document_text: str):
            return []

    class StubPrivacyService:
        def sanitize_evidence(self, *, matched_terms, evidence_excerpt):
            class Result:
                sanitized_terms = matched_terms
                sanitized_excerpt = "sanitized excerpt"

            return Result()

    orchestrator = DiscoveryOrchestrator(
        text_provider=StubTextProvider(),
        discovery_engine=StubDiscoveryEngine(),
        privacy_service=StubPrivacyService(),
        stale_scan_threshold_seconds=60,
    )
    monkeypatch.setattr(documents_api, "discovery_scan_executor", documents_api.DiscoveryScanExecutor(orchestrator))

    documents_api._process_discovery_scan_in_background(scan_id, user_id, document_id)

    verification_db = SessionLocal()
    try:
        persisted_scan = verification_db.query(DiscoveryScan).filter(DiscoveryScan.id == scan_id).one()
        assert persisted_scan.status == DISCOVERY_SCAN_STATUS_COMPLETE
        tracked_rows = verification_db.query(DiscoveryScanDocument).filter(DiscoveryScanDocument.scan_id == scan_id).all()
        findings = verification_db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == scan_id).all()
        assert len(tracked_rows) == 1
        assert len(findings) == 0
    finally:
        verification_db.close()


def test_background_discovery_closes_session_when_failure_recording_also_fails(monkeypatch) -> None:
    class TrackingSession:
        def __init__(self) -> None:
            self.close_count = 0
            self.rollback_count = 0

        def close(self) -> None:
            self.close_count += 1

        def rollback(self) -> None:
            self.rollback_count += 1

    background_session = TrackingSession()
    monkeypatch.setattr(documents_api, "SessionLocal", lambda: background_session)

    def fail_processing(*args, **kwargs):
        raise RuntimeError("processing failed")

    def fail_recording(*args, **kwargs):
        raise RuntimeError("failure recording failed")

    monkeypatch.setattr(documents_api.discovery_scan_executor, "process_existing", fail_processing)
    monkeypatch.setattr(documents_api.discovery_scan_executor, "mark_failed", fail_recording)

    documents_api._process_discovery_scan_in_background("scan-1", "user-1", "document-1")

    assert background_session.rollback_count == 2
    assert background_session.close_count == 1


def test_scheduling_failure_is_reraised_when_scan_failure_recording_also_fails(monkeypatch) -> None:
    class TrackingSession:
        def __init__(self) -> None:
            self.rollback_count = 0

        def rollback(self) -> None:
            self.rollback_count += 1

    class FailingBackgroundTasks:
        def add_task(self, func, *args, **kwargs):
            raise RuntimeError("scheduling failed")

    db = TrackingSession()
    scan = SimpleNamespace(id="scan-1", status=DISCOVERY_SCAN_STATUS_PENDING)
    monkeypatch.setattr(documents_api.discovery_scan_executor, "create_pending", lambda *args, **kwargs: scan)

    def fail_recording(*args, **kwargs):
        raise RuntimeError("failure recording failed")

    monkeypatch.setattr(documents_api.discovery_scan_executor, "mark_failed", fail_recording)

    with pytest.raises(RuntimeError, match="scheduling failed"):
        documents_api._trigger_discovery_scan_after_upload(
            db,
            FailingBackgroundTasks(),
            user_id="user-1",
            document_id="document-1",
        )

    assert db.rollback_count == 2


def test_genuine_background_discovery_failure_does_not_break_upload(monkeypatch) -> None:
    token = _token("upload-discovery-background-failure@example.com")
    document = _post_document(token, original_filename="statement.txt", mime_type="text/plain", file_size=32)
    assert document.status_code == 201
    document_id = document.json()["id"]

    def fail_extraction(document):
        raise RuntimeError("sensitive background failure text")

    monkeypatch.setattr(documents_api.discovery_scan_executor.orchestrator.text_provider, "get_text", fail_extraction)

    try:
        response = _upload_document(
            token,
            document_id,
            content=b"successfully persisted document content",
            filename="statement.txt",
            mime_type="text/plain",
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["upload_status"] == "COMPLETED"
        assert payload["discovery_scan"]["status"] == DISCOVERY_SCAN_STATUS_PENDING

        db = SessionLocal()
        try:
            saved = db.query(Document).filter(Document.id == document_id).one()
            assert saved.encryption_key_reference_encrypted is not None
            scan = db.query(DiscoveryScan).filter(DiscoveryScan.id == payload["discovery_scan"]["scan_id"]).one()
            assert scan.status == DISCOVERY_SCAN_STATUS_FAILED
            tracking = db.query(DiscoveryScanDocument).filter(DiscoveryScanDocument.scan_id == scan.id).one()
            assert tracking.status == DISCOVERY_DOCUMENT_STATUS_FAILED
            assert tracking.warning_code == DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED
            audit_text = " ".join(
                f"{entry.details} {entry.event_metadata}"
                for entry in db.query(AuditLog).filter(AuditLog.event_metadata.is_not(None)).all()
            )
            assert "sensitive background failure text" not in audit_text
        finally:
            db.close()
        assert documents_api.document_storage.exists(_storage_locator(document_id))
    finally:
        documents_api.document_storage.delete_permanently(_storage_locator(document_id))


def test_upload_survives_background_scheduling_failure(monkeypatch) -> None:
    token = _token("upload-discovery-scheduling-failure@example.com")
    document = _post_document(token, original_filename="statement.txt", mime_type="text/plain", file_size=32)
    assert document.status_code == 201
    document_id = document.json()["id"]
    plaintext = b"successfully persisted despite scheduling failure"

    def fail_scheduling(self, func, *args, **kwargs):
        raise RuntimeError("simulated scheduling failure")

    monkeypatch.setattr(BackgroundTasks, "add_task", fail_scheduling)

    try:
        response = _upload_document(
            token,
            document_id,
            content=plaintext,
            filename="statement.txt",
            mime_type="text/plain",
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["upload_status"] == "COMPLETED"
        assert payload["discovery_scan"] is None

        db = SessionLocal()
        try:
            saved = db.query(Document).filter(Document.id == document_id).one()
            assert saved.checksum_sha256 is None
            assert saved.encryption_key_reference_encrypted is not None
            scan = db.query(DiscoveryScan).one()
            assert scan.status == DISCOVERY_SCAN_STATUS_FAILED
            assert scan.completed_at is not None
        finally:
            db.close()
        assert documents_api.document_storage.exists(_storage_locator(document_id))
    finally:
        documents_api.document_storage.delete_permanently(_storage_locator(document_id))


def test_upload_survives_scan_creation_audit_failure_without_scheduling(monkeypatch) -> None:
    token = _token("upload-discovery-audit-failure@example.com")
    document = _post_document(token, original_filename="statement.txt", mime_type="text/plain", file_size=32)
    assert document.status_code == 201
    document_id = document.json()["id"]
    plaintext = b"successfully persisted despite discovery audit failure"
    scheduled = {"called": False}

    def fail_audit(*args, **kwargs):
        raise RuntimeError("simulated discovery audit failure")

    def capture_scheduling(self, func, *args, **kwargs):
        scheduled["called"] = True

    monkeypatch.setattr(documents_api.discovery_scan_executor.orchestrator, "_audit", fail_audit)
    monkeypatch.setattr(BackgroundTasks, "add_task", capture_scheduling)

    try:
        response = _upload_document(
            token,
            document_id,
            content=plaintext,
            filename="statement.txt",
            mime_type="text/plain",
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["upload_status"] == "COMPLETED"
        assert payload["discovery_scan"] is None
        assert scheduled["called"] is False

        db = SessionLocal()
        try:
            saved = db.query(Document).filter(Document.id == document_id).one()
            assert saved.checksum_sha256 is None
            assert saved.encryption_key_reference_encrypted is not None
            assert saved.original_filename == "statement.txt"
            assert saved.mime_type == "text/plain"
            assert saved.file_size == len(plaintext)
            scan = db.query(DiscoveryScan).one()
            assert scan.status == DISCOVERY_SCAN_STATUS_PENDING
            assert scan.completed_at is None
        finally:
            db.close()
        assert documents_api.document_storage.exists(_storage_locator(document_id))
    finally:
        documents_api.document_storage.delete_permanently(_storage_locator(document_id))


def test_upload_still_succeeds_when_post_upload_discovery_raises(monkeypatch) -> None:
    token = _token("upload-discovery-failure@example.com")
    document = _post_document(token, original_filename="statement.txt", mime_type="text/plain", file_size=32)
    assert document.status_code == 201
    document_id = document.json()["id"]
    plaintext = b"successfully persisted document content"

    def fail_discovery(*args, **kwargs):
        raise RuntimeError("simulated post-upload discovery failure")

    monkeypatch.setattr(documents_api, "_trigger_discovery_scan_after_upload", fail_discovery)

    try:
        response = _upload_document(
            token,
            document_id,
            content=plaintext,
            filename="statement.txt",
            mime_type="text/plain",
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["upload_status"] == "COMPLETED"
        assert payload["discovery_scan"] is None

        db = SessionLocal()
        try:
            saved = db.query(Document).filter(Document.id == document_id).one()
            assert saved.checksum_sha256 is None
            assert saved.encryption_key_reference_encrypted is not None
            assert saved.original_filename == "statement.txt"
            assert saved.mime_type == "text/plain"
            assert saved.file_size == len(plaintext)
        finally:
            db.close()

        assert documents_api.document_storage.exists(_storage_locator(document_id))
    finally:
        documents_api.document_storage.delete_permanently(_storage_locator(document_id))


def test_empty_discovery_scan_request_remains_rejected() -> None:
    token = _token("empty-discovery-scan@example.com")

    response = client.post(
        "/discovery/scans",
        headers={"Authorization": f"Bearer {token}"},
        json={"document_ids": []},
    )

    assert response.status_code == 422
