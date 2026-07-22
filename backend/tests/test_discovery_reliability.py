import os
from dataclasses import dataclass

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.database.connection import Base, SessionLocal, engine
from app.models.discovery import DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS, DiscoveryScan, EvidenceFinding
from app.models.document import Document
from app.models.user import User
from app.services.discovery_orchestrator import DiscoveryScanExecutor, DiscoveryOrchestrationError, DiscoveryOrchestrator


@dataclass(frozen=True)
class Candidate:
    category: str = "RETIREMENT_INDICATOR"
    matched_terms: list[str] = None
    confidence_score: int = 85


class MixedTextProvider:
    def get_text(self, document: Document) -> str:
        if document.id == "bad-doc":
            raise DiscoveryOrchestrationError("Document format extraction is not supported")
        return "retirement rollover"


class FindingEngine:
    def analyze_text(self, document_text: str):
        return [Candidate(matched_terms=["retirement"])]


class Privacy:
    def sanitize_evidence(self, *, matched_terms, evidence_excerpt):
        class Result:
            sanitized_terms = matched_terms
            sanitized_excerpt = None
        return Result()


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _seed_documents() -> None:
    db = SessionLocal()
    try:
        user = User(id="user-1", email="user-1@example.com", password_hash="hash")
        good = Document(id="good-doc", user_id=user.id, document_type="ACCOUNT_STATEMENT", document_name="Good")
        bad = Document(id="bad-doc", user_id=user.id, document_type="ACCOUNT_STATEMENT", document_name="Bad")
        db.add_all([user, good, bad])
        db.commit()
    finally:
        db.close()


def test_partial_scan_success_creates_findings_and_warnings_status() -> None:
    _seed_documents()
    events = []
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=MixedTextProvider(),
            discovery_engine=FindingEngine(),
            privacy_service=Privacy(),
            audit_logger=lambda db, user_id, event_type, details: events.append((event_type, details)),
        )
        scan = orchestrator.run_scan(db, user_id="user-1", document_ids=["good-doc", "bad-doc"])
        assert scan.status == DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS
        assert scan.documents_processed == 1
        assert db.query(EvidenceFinding).count() == 1
        assert any(event_type == "discovery_document_failed" for event_type, _details in events)
    finally:
        db.close()


def test_unsupported_document_does_not_destroy_valid_findings() -> None:
    _seed_documents()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=MixedTextProvider(), discovery_engine=FindingEngine(), privacy_service=Privacy())
        orchestrator.run_scan(db, user_id="user-1", document_ids=["good-doc", "bad-doc"])
        finding = db.query(EvidenceFinding).one()
        assert finding.document_id == "good-doc"
        assert finding.get_matched_terms() == '["retirement"]'
    finally:
        db.close()


def test_audit_events_do_not_contain_sensitive_data() -> None:
    _seed_documents()
    events = []
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=MixedTextProvider(),
            discovery_engine=FindingEngine(),
            privacy_service=Privacy(),
            audit_logger=lambda db, user_id, event_type, details: events.append((event_type, details)),
        )
        orchestrator.run_scan(db, user_id="user-1", document_ids=["good-doc", "bad-doc"])
        details = " ".join(detail for _event_type, detail in events)
        assert "retirement rollover" not in details
        assert "retirement" not in details
        assert "Document format extraction is not supported" not in details
    finally:
        db.close()


def test_scan_executor_delegates_to_orchestrator() -> None:
    _seed_documents()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(text_provider=MixedTextProvider(), discovery_engine=FindingEngine(), privacy_service=Privacy())
        executor = DiscoveryScanExecutor(orchestrator)
        scan = executor.process(db, user_id="user-1", document_ids=["good-doc"])
        assert isinstance(scan, DiscoveryScan)
        assert scan.documents_processed == 1
    finally:
        db.close()