import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.database.connection import Base, SessionLocal, engine
from app.services.document_content_encryption import DocumentContentEncryptionError
from app.models.discovery import (
    DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS,
    DISCOVERY_SCAN_STATUS_FAILED,
    DiscoveryScan,
    EvidenceFinding,
)
from app.models.discovery_scan_document import (
    DISCOVERY_DOCUMENT_STATUS_COMPLETED,
    DISCOVERY_DOCUMENT_STATUS_FAILED,
    DISCOVERY_DOCUMENT_STATUS_SKIPPED,
    DISCOVERY_DOCUMENT_WARNING_EMPTY_DOCUMENT,
    DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED,
    DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION,
    DiscoveryScanDocument,
)
from app.models.document import DOCUMENT_STORAGE_PENDING, DOCUMENT_STORAGE_STORED, Document
from app.models.user import User
from app.services.document_content_encryption import document_content_encryption_service
from app.services.discovery_orchestrator import (
    DiscoveryOrchestrationError,
    DiscoveryOrchestrator,
    EncryptedDocumentTextProvider,
    UnsupportedDocumentExtractionError,
)


class MemoryStorage:
    def __init__(self, encrypted_bytes: bytes) -> None:
        self.encrypted_bytes = encrypted_bytes
        self.requested_locator: str | None = None

    def read_encrypted(self, locator: str, **kwargs) -> bytes:
        self.requested_locator = locator
        if locator != "opaque/random/non-derivable-object-key.lgdoc":
            raise RuntimeError("wrong locator")
        return self.encrypted_bytes


class FailingStorage:
    def read_encrypted(self, locator: str, **kwargs) -> bytes:
        raise RuntimeError("storage failure")


class FailingExtractionService:
    def extract_from_bytes(self, content: bytes, *, mime_type: str | None = None):
        raise RuntimeError("unexpected extraction failure")


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
            storage_state=DOCUMENT_STORAGE_STORED,
            ciphertext_sha256=encrypted.checksum_sha256,
            ciphertext_size=len(encrypted.encrypted_bytes),
        )
        document.set_storage_reference("opaque/random/non-derivable-object-key.lgdoc")
        db.add_all([user, document])
        db.commit()
        return document_id, encrypted.encrypted_bytes
    finally:
        db.close()


def test_text_document_flows_through_extraction() -> None:
    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="text/plain", plaintext=b"  retirement\r\n rollover  ")
    storage = MemoryStorage(encrypted_bytes)
    provider = EncryptedDocumentTextProvider(storage=storage)
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).one()
        assert provider.get_text(document) == "retirement\nrollover"
        assert storage.requested_locator == "opaque/random/non-derivable-object-key.lgdoc"
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


def test_unsupported_provider_result_has_dedicated_exception_type() -> None:
    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="application/pdf", plaintext=b"%PDF-1.7 content")
    provider = EncryptedDocumentTextProvider(storage=MemoryStorage(encrypted_bytes))
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).one()
        with pytest.raises(UnsupportedDocumentExtractionError):
            provider.get_text(document)
    finally:
        db.close()


def test_unsupported_formats_are_skipped_with_warnings() -> None:
    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="application/pdf", plaintext=b"%PDF-1.7 content")
    provider = EncryptedDocumentTextProvider(storage=MemoryStorage(encrypted_bytes))
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=provider)
        scan = orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])

        assert scan.status == DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS
        assert scan.documents_processed == 0
        tracking = db.query(DiscoveryScanDocument).one()
        assert tracking.status == DISCOVERY_DOCUMENT_STATUS_SKIPPED
        assert tracking.warning_code == DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION
        assert db.query(EvidenceFinding).count() == 0
    finally:
        db.close()


def test_missing_key_and_storage_failure_are_not_unsupported_extraction() -> None:
    missing_key_document = Document(
        id="550e8400-e29b-41d4-a716-446655440001",
        user_id="user-1",
        document_type="ACCOUNT_STATEMENT",
        document_name="Missing key",
        mime_type="text/plain",
        storage_state=DOCUMENT_STORAGE_STORED,
    )
    missing_key_provider = EncryptedDocumentTextProvider(storage=MemoryStorage(b"unused"))
    with pytest.raises(DiscoveryOrchestrationError) as missing_key_error:
        missing_key_provider.get_text(missing_key_document)
    assert not isinstance(missing_key_error.value, UnsupportedDocumentExtractionError)

    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="text/plain", plaintext=b"content")
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).one()
        with pytest.raises(RuntimeError) as storage_error:
            EncryptedDocumentTextProvider(storage=FailingStorage()).get_text(document)
        assert not isinstance(storage_error.value, UnsupportedDocumentExtractionError)
    finally:
        db.close()


def test_pending_document_is_not_discovery_eligible() -> None:
    document = Document(
        id="550e8400-e29b-41d4-a716-446655440009",
        user_id="user-1",
        document_type="ACCOUNT_STATEMENT",
        document_name="Pending",
        mime_type="text/plain",
        storage_state=DOCUMENT_STORAGE_PENDING,
        encryption_key_reference_encrypted="not-used",
    )

    with pytest.raises(DiscoveryOrchestrationError, match="eligible storage state"):
        EncryptedDocumentTextProvider(storage=MemoryStorage(b"unused")).get_text(document)


def test_stored_document_without_locator_fails_closed() -> None:
    document = Document(
        id="550e8400-e29b-41d4-a716-446655440010",
        user_id="user-1",
        document_type="ACCOUNT_STATEMENT",
        document_name="Missing locator",
        mime_type="text/plain",
        storage_state=DOCUMENT_STORAGE_STORED,
        encryption_key_reference_encrypted="not-used",
    )

    with pytest.raises(DiscoveryOrchestrationError, match="locator is unavailable"):
        EncryptedDocumentTextProvider(storage=MemoryStorage(b"unused")).get_text(document)


def test_tampered_encrypted_locator_fails_closed() -> None:
    document = Document(
        id="550e8400-e29b-41d4-a716-446655440011",
        user_id="user-1",
        document_type="ACCOUNT_STATEMENT",
        document_name="Tampered locator",
        mime_type="text/plain",
        storage_state=DOCUMENT_STORAGE_STORED,
        encryption_key_reference_encrypted="not-used",
        storage_reference_encrypted="tampered",
    )

    with pytest.raises(DiscoveryOrchestrationError, match="locator is unavailable"):
        EncryptedDocumentTextProvider(storage=MemoryStorage(b"unused")).get_text(document)


def test_decryption_and_unexpected_extraction_failures_are_not_unsupported() -> None:
    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="text/plain", plaintext=b"content")
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).one()

        with pytest.raises(DocumentContentEncryptionError) as decryption_error:
            EncryptedDocumentTextProvider(storage=MemoryStorage(b"x" + encrypted_bytes[1:])).get_text(document)
        assert not isinstance(decryption_error.value, UnsupportedDocumentExtractionError)

        with pytest.raises(RuntimeError) as extraction_error:
            EncryptedDocumentTextProvider(
                storage=MemoryStorage(encrypted_bytes),
                extraction_service=FailingExtractionService(),
            ).get_text(document)
        assert not isinstance(extraction_error.value, UnsupportedDocumentExtractionError)
    finally:
        db.close()


def test_unexpected_supported_format_extraction_failure_remains_failed() -> None:
    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="text/plain", plaintext=b"content")
    provider = EncryptedDocumentTextProvider(
        storage=MemoryStorage(encrypted_bytes),
        extraction_service=FailingExtractionService(),
    )
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=provider)
        with pytest.raises(DiscoveryOrchestrationError):
            orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])

        scan = db.query(DiscoveryScan).one()
        assert scan.status == DISCOVERY_SCAN_STATUS_FAILED
        tracking = db.query(DiscoveryScanDocument).one()
        assert tracking.status == DISCOVERY_DOCUMENT_STATUS_FAILED
        assert tracking.warning_code == DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED
    finally:
        db.close()


def test_unsupported_formats_do_not_create_partial_findings() -> None:
    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="application/pdf", plaintext=b"%PDF-1.7 content")
    provider = EncryptedDocumentTextProvider(storage=MemoryStorage(encrypted_bytes))
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=provider)
        orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])
        assert db.query(EvidenceFinding).count() == 0
    finally:
        db.close()


def test_empty_documents_complete_with_warnings() -> None:
    document_id, encrypted_bytes = _create_document_with_encrypted_content(mime_type="text/plain", plaintext=b"   \n  \r\n  ")
    provider = EncryptedDocumentTextProvider(storage=MemoryStorage(encrypted_bytes))
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=provider)
        scan = orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])

        assert scan.status == DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS
        assert db.query(EvidenceFinding).count() == 0
        tracking = db.query(DiscoveryScanDocument).one()
        assert tracking.status == DISCOVERY_DOCUMENT_STATUS_COMPLETED
        assert tracking.warning_code == DISCOVERY_DOCUMENT_WARNING_EMPTY_DOCUMENT
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
