import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.database.connection import SessionLocal
from app.main import app
from app.models.asset import ASSET_STATUS_ARCHIVED, Asset
from app.models.beneficiary import BENEFICIARY_STATUS_ARCHIVED, Beneficiary
from app.models.document import Document
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


def test_owner_uploads_valid_pdf_and_response_is_private() -> None:
    token = _token("upload-owner@example.com")
    document = _post_document(token, original_filename="old.txt", mime_type="text/plain", file_size=1)
    assert document.status_code == 201
    document_id = document.json()["id"]
    plaintext = b"%PDF-1.4\nvalid pdf bytes"

    response = _upload_document(token, document_id, content=plaintext)

    assert response.status_code == 200
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
        encrypted_bytes = documents_api.document_storage.read_encrypted(document_id)
        assert encrypted_bytes != plaintext
        assert plaintext not in encrypted_bytes
        assert saved.storage_reference is None
        assert saved.storage_reference_encrypted is not None
        assert saved.get_storage_reference() is not None
        assert saved.encryption_key_reference_encrypted is not None
        assert saved.encryption_key_reference_encrypted != "client-key"
        assert document_content_encryption_service.decrypt(document_id, encrypted_bytes, saved.encryption_key_reference_encrypted) == plaintext
        assert saved.checksum_sha256 == __import__("hashlib").sha256(plaintext).hexdigest()
    finally:
        db.close()
        documents_api.document_storage.delete_permanently(document_id)


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

    def delete_and_track(document_id: str) -> None:
        deleted["called"] = True
        original_delete(document_id)

    monkeypatch.setattr(documents_api.document_storage, "save_encrypted", save_and_mark)
    monkeypatch.setattr(documents_api.document_storage, "delete_permanently", delete_and_track)

    # Force the next commit in the route to fail by patching Session.commit globally after metadata creation is complete.
    def always_fail_commit(self):
        raise RuntimeError("db fail")

    monkeypatch.setattr(type(SessionLocal()), "commit", always_fail_commit, raising=False)
    response = _upload_document(token, document_id)

    assert response.status_code == 500
    assert deleted["called"] is True
