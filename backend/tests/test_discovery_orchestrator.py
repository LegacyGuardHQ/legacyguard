import os
from dataclasses import dataclass

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.database.connection import Base, SessionLocal, engine
from app.models.discovery import DISCOVERY_SCAN_STATUS_COMPLETE, DISCOVERY_SCAN_STATUS_FAILED, DiscoveryScan, EvidenceFinding
from app.models.document import Document
from app.models.user import User
from app.services.discovery_orchestrator import DiscoveryOrchestrationError, DiscoveryOrchestrator


@dataclass(frozen=True)
class FakeCandidate:
    category: str
    matched_terms: list[str]
    confidence_score: int


class FakeTextProvider:
    def __init__(self, text: str = "retirement rollover") -> None:
        self.text = text
        self.called = False

    def get_text(self, document: Document) -> str:
        self.called = True
        return self.text


class FakeDiscoveryEngine:
    def __init__(self) -> None:
        self.called = False

    def analyze_text(self, document_text: str) -> list[FakeCandidate]:
        self.called = True
        return [FakeCandidate(category="RETIREMENT_INDICATOR", matched_terms=["retirement"], confidence_score=85)]


class FailingDiscoveryEngine:
    def analyze_text(self, document_text: str) -> list[FakeCandidate]:
        raise RuntimeError("sensitive internal failure")


class FakePrivacyService:
    def __init__(self) -> None:
        self.called = False

    def sanitize_evidence(self, *, matched_terms, evidence_excerpt):
        self.called = True

        class Result:
            sanitized_terms = matched_terms
            sanitized_excerpt = "sanitized excerpt"

        return Result()


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_user_and_document(user_id: str = "user-1", document_id: str = "doc-1") -> tuple[str, str]:
    db = SessionLocal()
    try:
        user = User(id=user_id, email=f"{user_id}@example.com", password_hash="hash")
        document = Document(id=document_id, user_id=user_id, document_type="ACCOUNT_STATEMENT", document_name="Statement")
        db.add_all([user, document])
        db.commit()
        return user.id, document.id
    finally:
        db.close()


def test_orchestrator_creates_discovery_scan() -> None:
    _user_id, document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=FakeTextProvider(), discovery_engine=FakeDiscoveryEngine(), privacy_service=FakePrivacyService())

        scan = orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])

        assert scan.status == DISCOVERY_SCAN_STATUS_COMPLETE
        assert scan.documents_processed == 1
    finally:
        db.close()


def test_orchestrator_rejects_documents_owned_by_another_user() -> None:
    _create_user_and_document(user_id="owner", document_id="owned-doc")
    db = SessionLocal()
    try:
        db.add(User(id="other", email="other@example.com", password_hash="hash"))
        db.commit()
        orchestrator = DiscoveryOrchestrator(text_provider=FakeTextProvider(), discovery_engine=FakeDiscoveryEngine(), privacy_service=FakePrivacyService())

        with pytest.raises(DiscoveryOrchestrationError):
            orchestrator.run_scan(db, user_id="other", document_ids=["owned-doc"])

        failed_scan = db.query(DiscoveryScan).one()
        assert failed_scan.status == DISCOVERY_SCAN_STATUS_FAILED
    finally:
        db.close()


def test_orchestrator_calls_discovery_engine() -> None:
    _user_id, document_id = _create_user_and_document()
    engine = FakeDiscoveryEngine()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=FakeTextProvider(), discovery_engine=engine, privacy_service=FakePrivacyService())

        orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])

        assert engine.called is True
    finally:
        db.close()


def test_orchestrator_calls_privacy_service() -> None:
    _user_id, document_id = _create_user_and_document()
    privacy_service = FakePrivacyService()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=FakeTextProvider(), discovery_engine=FakeDiscoveryEngine(), privacy_service=privacy_service)

        orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])

        assert privacy_service.called is True
    finally:
        db.close()


def test_orchestrator_creates_evidence_finding() -> None:
    _user_id, document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=FakeTextProvider(), discovery_engine=FakeDiscoveryEngine(), privacy_service=FakePrivacyService())

        scan = orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])

        finding = db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == scan.id).one()
        assert finding.document_id == document_id
        assert finding.category == "RETIREMENT_INDICATOR"
        assert finding.confidence_score == 85
    finally:
        db.close()


def test_orchestrator_stores_encrypted_evidence_fields() -> None:
    _user_id, document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=FakeTextProvider(), discovery_engine=FakeDiscoveryEngine(), privacy_service=FakePrivacyService())

        scan = orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])

        finding = db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == scan.id).one()
        assert finding.matched_terms_encrypted is not None
        assert finding.evidence_excerpt_encrypted is not None
        assert "retirement" not in finding.matched_terms_encrypted
        assert "sanitized excerpt" not in finding.evidence_excerpt_encrypted
        assert finding.get_matched_terms() == '["retirement"]'
        assert finding.get_evidence_excerpt() == "sanitized excerpt"
    finally:
        db.close()


def test_orchestrator_marks_failed_scans_correctly() -> None:
    _user_id, document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=FakeTextProvider(), discovery_engine=FailingDiscoveryEngine(), privacy_service=FakePrivacyService())

        with pytest.raises(DiscoveryOrchestrationError):
            orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])

        scan = db.query(DiscoveryScan).one()
        assert scan.status == DISCOVERY_SCAN_STATUS_FAILED
    finally:
        db.close()