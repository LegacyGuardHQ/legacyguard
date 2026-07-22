import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.database.connection import Base, SessionLocal, engine
from app.models.discovery import DISCOVERY_SCAN_STATUS_FAILED, DiscoveryScan, EvidenceFinding
from app.models.document import Document
from app.models.user import User
from app.services.document_content_encryption import document_content_encryption_service
from app.services.discovery_orchestrator import DiscoveryOrchestrationError, DiscoveryOrchestrator, EncryptedDocumentTextProvider


class MemoryStorage:
    def __init__(self, encrypted_bytes: bytes) -> None:
        self.encrypted_bytes = encrypted_bytes

    def read_encrypted(self, document_id: str) -> bytes:
        return self.encrypted_bytes


class CapturingDiscoveryEngine:
    def __init__(self) -> None:
        self.received_text: str | None = None

    def analyze_text(self, document_text: str):
        self.received_text = document_text
        return []


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_document_with_encrypted_content(*, mime_type: str, plaintext: bytes) -> tuple[str, bytes]:
    document_id = "550e8400-e29b-41d4-a716-446655440000"
    encrypted = document_content_encryption_service.encrypt(document_id, plaintext)
    db = SessionLocal()
    try:
        user = User(id="user-1", email="user-1@example.com", password_hash="hash")
        document = Document(
            id=document_id,
            user_id=user.id,
            document_type="ACCOUNT_STATEMENT",
            document_name="Statement",
            mime_type=mime_type,
            encryption_key_reference_encrypted=encrypted.encrypted_key_reference,
        )
        db.add_all([user, document])
        db.commit()
        return document_id, encrypted.encrypted_bytes
    finally:
        db.close()


def test_text_document_flows_through_extraction() -> None:
    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="text/plain", plaintext=b"  retirement\r\n rollover  ")
    provider = EncryptedDocumentTextProvider(storage=MemoryStorage(encrypted_bytes))
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).one()
        assert provider.get_text(document) == "retirement\nrollover"
    finally:
        db.close()


def test_discovery_receives_normalized_text() -> None:
    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="text/plain", plaintext=b"  policy\r\n coverage  ")
    engine = CapturingDiscoveryEngine()
    provider = EncryptedDocumentTextProvider(storage=MemoryStorage(encrypted_bytes))
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=provider, discovery_engine=engine)
        orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])
        assert engine.received_text == "policy\ncoverage"
    finally:
        db.close()


def test_unsupported_formats_fail_safely() -> None:
    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="application/pdf", plaintext=b"%PDF-1.7 content")
    provider = EncryptedDocumentTextProvider(storage=MemoryStorage(encrypted_bytes))
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=provider)
        with pytest.raises(DiscoveryOrchestrationError) as exc_info:
            orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])
        assert str(exc_info.value) == "Discovery scan failed"
        scan = db.query(DiscoveryScan).one()
        assert scan.status == DISCOVERY_SCAN_STATUS_FAILED
    finally:
        db.close()


def test_unsupported_formats_do_not_create_partial_findings() -> None:
    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="application/pdf", plaintext=b"%PDF-1.7 content")
    provider = EncryptedDocumentTextProvider(storage=MemoryStorage(encrypted_bytes))
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=provider)
        with pytest.raises(DiscoveryOrchestrationError):
            orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])
        assert db.query(EvidenceFinding).count() == 0
    finally:
        db.close()


def test_no_plaintext_document_persistence_occurs() -> None:
    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="text/plain", plaintext=b"retirement account clue")
    engine = CapturingDiscoveryEngine()
    provider = EncryptedDocumentTextProvider(storage=MemoryStorage(encrypted_bytes))
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=provider, discovery_engine=engine)
        orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])
        document = db.query(Document).filter(Document.id == document_id).one()
        assert not hasattr(document, "extracted_text")
        assert "retirement account clue" not in (document.description_encrypted or "")
    finally:
        db.close()