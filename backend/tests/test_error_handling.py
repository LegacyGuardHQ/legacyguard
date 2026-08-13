import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.api import documents as documents_api
from app.main import app
from app.services.document_content_encryption import (
    DocumentContentEncryptionError,
    document_content_encryption_service,
)
from app.services.encryption import encryption_service
from app.services.rate_limit import rate_limiter

client = TestClient(app, raise_server_exceptions=False)


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


def _create_document(token: str) -> str:
    response = client.post(
        "/documents",
        headers={"Authorization": f"Bearer {token}"},
        json={"document_type": "WILL", "document_name": "Estate Will"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_unexpected_upload_preparation_failure_is_server_error(monkeypatch) -> None:
    token = _token("upload-unexpected@example.com")
    document_id = _create_document(token)

    def explode(document_id: str, plaintext: bytes):
        raise RuntimeError("unexpected encryption backend failure")

    monkeypatch.setattr(documents_api.document_content_encryption_service, "encrypt", explode)
    response = client.post(
        f"/documents/{document_id}/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("upload.pdf", b"%PDF-1.4\nbytes", "application/pdf")},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Document upload failed"


def test_malformed_document_key_reference_raises_domain_error() -> None:
    encrypted_key_reference = encryption_service.encrypt("not-a-valid-key-reference")

    with pytest.raises(DocumentContentEncryptionError):
        document_content_encryption_service.decrypt("document-1", b"ciphertext", encrypted_key_reference)


def test_undecryptable_document_key_reference_raises_domain_error() -> None:
    with pytest.raises(DocumentContentEncryptionError):
        document_content_encryption_service.decrypt("document-1", b"ciphertext", "not-encrypted-at-all")
