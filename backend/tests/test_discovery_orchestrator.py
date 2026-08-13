import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import BoundedSemaphore, Lock
from unittest.mock import Mock

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.api import documents as documents_api
from app.config import settings
from app.database.connection import Base, SessionLocal, engine
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
    DISCOVERY_DOCUMENT_STATUS_COMPLETED,
    DISCOVERY_DOCUMENT_STATUS_FAILED,
    DISCOVERY_DOCUMENT_STATUS_SKIPPED,
    DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED,
    DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION,
    DiscoveryScanDocument,
)
from app.models.document import Document
from app.models.user import User
from app.services.audit import log_event
from app.services.discovery_orchestrator import (
    DISCOVERY_COMPLETED,
    DISCOVERY_DOCUMENT_COMPLETED,
    DISCOVERY_DOCUMENT_SKIPPED,
    DISCOVERY_FAILED,
    DISCOVERY_STARTED,
    EVIDENCE_FINDING_CREATED,
    DiscoveryOrchestrationError,
    DiscoveryOrchestrator,
    DiscoveryScanAlreadyClaimedError,
    EncryptedDocumentTextProvider,
    UnsupportedDocumentExtractionError,
)
from app.services import discovery_orchestrator as discovery_orchestrator_module


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


class UnsupportedTextProvider:
    def get_text(self, document: Document) -> str:
        raise UnsupportedDocumentExtractionError("Document format extraction is not supported")


class FakeDiscoveryEngine:
    def __init__(self) -> None:
        self.called = False

    def analyze_text(self, document_text: str) -> list[FakeCandidate]:
        self.called = True
        return [FakeCandidate(category="RETIREMENT_INDICATOR", matched_terms=["retirement"], confidence_score=85)]


class TwoCandidateDiscoveryEngine:
    def analyze_text(self, document_text: str) -> list[FakeCandidate]:
        return [
            FakeCandidate(category="RETIREMENT_INDICATOR", matched_terms=["retirement"], confidence_score=85),
            FakeCandidate(category="INSURANCE_INDICATOR", matched_terms=["policy"], confidence_score=80),
        ]


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


def test_scan_executor_caps_concurrent_scan_processing(monkeypatch: pytest.MonkeyPatch) -> None:
    concurrency_limit = 2
    monkeypatch.setattr(
        discovery_orchestrator_module,
        "_discovery_scan_slots",
        BoundedSemaphore(concurrency_limit),
    )
    state_lock = Lock()
    active = 0
    peak_active = 0

    class ObservedOrchestrator:
        def run_scan(self, db, *, user_id: str, document_ids: list[str]):
            nonlocal active, peak_active
            with state_lock:
                active += 1
                peak_active = max(peak_active, active)
            try:
                time.sleep(0.03)
                return user_id
            finally:
                with state_lock:
                    active -= 1

    executor = discovery_orchestrator_module.DiscoveryScanExecutor(ObservedOrchestrator())
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(
                lambda index: executor.process(object(), user_id=f"user-{index}", document_ids=[]),
                range(8),
            )
        )

    assert len(results) == 8
    assert peak_active == concurrency_limit


def test_documents_api_builds_discovery_orchestrator_with_configured_stale_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "discovery_stale_scan_threshold_seconds", 123)

    orchestrator = documents_api._build_discovery_orchestrator()

    assert orchestrator.stale_scan_threshold_seconds == 123


def test_discovery_text_provider_uses_configured_storage_root(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    configured_root = tmp_path / "configured-discovery-storage"
    monkeypatch.setattr(settings, "document_storage_root", str(configured_root))

    provider = EncryptedDocumentTextProvider()

    assert provider.storage.root == configured_root.resolve()


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


def test_orchestrator_processes_precreated_scan_without_creating_duplicate() -> None:
    _user_id, document_id = _create_user_and_document()
    text_provider = FakeTextProvider()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=text_provider,
            discovery_engine=FakeDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
        )

        pending_scan = orchestrator.create_scan(db, user_id="user-1")

        assert pending_scan.status == DISCOVERY_SCAN_STATUS_PENDING
        assert text_provider.called is False
        assert db.query(DiscoveryScan).count() == 1

        completed_scan = orchestrator.process_scan(
            db,
            scan_id=pending_scan.id,
            user_id="user-1",
            document_ids=[document_id],
        )

        assert completed_scan.id == pending_scan.id
        assert completed_scan.status == DISCOVERY_SCAN_STATUS_COMPLETE
        assert completed_scan.documents_processed == 1
        assert completed_scan.started_at is not None
        claimed_started_at = completed_scan.started_at
        assert text_provider.called is True
        assert db.query(DiscoveryScan).count() == 1
        assert db.query(DiscoveryScanDocument).filter(DiscoveryScanDocument.scan_id == pending_scan.id).count() == 1
        assert db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == pending_scan.id).count() == 1

        with pytest.raises(DiscoveryScanAlreadyClaimedError, match="Discovery scan is not pending"):
            orchestrator.process_scan(
                db,
                scan_id=pending_scan.id,
                user_id="user-1",
                document_ids=[document_id],
            )

        assert db.query(DiscoveryScanDocument).filter(DiscoveryScanDocument.scan_id == pending_scan.id).count() == 1
        assert db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == pending_scan.id).count() == 1
        db.refresh(completed_scan)
        assert completed_scan.started_at == claimed_started_at
    finally:
        db.close()


def test_orchestrator_rejects_processing_a_nonpending_scan() -> None:
    _user_id, document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=FakeTextProvider(),
            discovery_engine=FakeDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
        )

        with pytest.raises(DiscoveryOrchestrationError, match="Discovery scan not found"):
            orchestrator.process_scan(
                db,
                scan_id="missing-scan",
                user_id="user-1",
                document_ids=[document_id],
            )
    finally:
        db.close()


def test_orchestrator_recovers_stale_running_scans_without_duplicate_artifacts() -> None:
    _user_id, document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=FakeTextProvider(),
            discovery_engine=FakeDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
            stale_scan_threshold_seconds=60,
        )

        scan = orchestrator.create_scan(db, user_id="user-1")
        scan.status = DISCOVERY_SCAN_STATUS_RUNNING
        scan.started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        stale_tracking = DiscoveryScanDocument(
            id="tracking-old",
            scan_id=scan.id,
            document_id=document_id,
            status=DISCOVERY_DOCUMENT_STATUS_COMPLETED,
        )
        stale_finding = EvidenceFinding(
            id="finding-old",
            scan_id=scan.id,
            document_id=document_id,
            category="OLD_CATEGORY",
            confidence_score=99.0,
        )
        db.add_all([stale_tracking, stale_finding])
        db.commit()
        stale_tracking_id = stale_tracking.id
        stale_finding_id = stale_finding.id

        completed_scan = orchestrator.process_scan(
            db,
            scan_id=scan.id,
            user_id="user-1",
            document_ids=[document_id],
        )

        assert completed_scan.status == DISCOVERY_SCAN_STATUS_COMPLETE
        assert completed_scan.documents_processed == 1
        tracked_rows = db.query(DiscoveryScanDocument).filter(DiscoveryScanDocument.scan_id == scan.id).all()
        findings = db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == scan.id).all()
        assert len(tracked_rows) == 1
        assert len(findings) == 1
        assert tracked_rows[0].id != stale_tracking_id
        assert findings[0].id != stale_finding_id
    finally:
        db.close()


@pytest.mark.parametrize(
    "existing_status",
    [
        DISCOVERY_SCAN_STATUS_RUNNING,
        DISCOVERY_SCAN_STATUS_COMPLETE,
        DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS,
        DISCOVERY_SCAN_STATUS_FAILED,
    ],
)
def test_nonpending_scan_replays_are_non_mutating(existing_status: str) -> None:
    _user_id, document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=FakeTextProvider(),
            discovery_engine=FakeDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
        )
        scan = orchestrator.create_scan(db, user_id="user-1")
        scan_id = scan.id
        scan.status = existing_status
        db.commit()
        audits_before = db.query(AuditLog).count()

        with pytest.raises(DiscoveryScanAlreadyClaimedError, match="Discovery scan is not pending"):
            orchestrator.process_scan(
                db,
                scan_id=scan_id,
                user_id="user-1",
                document_ids=[document_id],
            )
    finally:
        db.close()

    verification_db = SessionLocal()
    try:
        assert verification_db.query(DiscoveryScan).filter(DiscoveryScan.id == scan_id).one().status == existing_status
        assert verification_db.query(DiscoveryScanDocument).filter(DiscoveryScanDocument.scan_id == scan_id).count() == 0
        assert verification_db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == scan_id).count() == 0
        assert verification_db.query(AuditLog).count() == audits_before
    finally:
        verification_db.close()


def test_orchestrator_rejects_scan_ownership_mismatch_without_processing() -> None:
    _user_id, document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        db.add(User(id="other-user", email="other-user@example.com", password_hash="hash"))
        db.commit()
        orchestrator = DiscoveryOrchestrator(
            text_provider=FakeTextProvider(),
            discovery_engine=FakeDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
        )
        pending_scan = orchestrator.create_scan(db, user_id="user-1")

        with pytest.raises(DiscoveryOrchestrationError, match="Discovery scan not found"):
            orchestrator.process_scan(
                db,
                scan_id=pending_scan.id,
                user_id="other-user",
                document_ids=[document_id],
            )

        db.refresh(pending_scan)
        assert pending_scan.status == DISCOVERY_SCAN_STATUS_PENDING
        assert pending_scan.started_at is None
        assert db.query(DiscoveryScanDocument).count() == 0
        assert db.query(EvidenceFinding).count() == 0
    finally:
        db.close()


def test_mark_scan_failed_returns_none_for_unknown_scan() -> None:
    _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=FakeTextProvider(),
            discovery_engine=FakeDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
        )

        assert orchestrator.mark_scan_failed(db, scan_id="missing-scan", user_id="user-1") is None
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

def test_orchestrator_tracks_completed_document() -> None:
    from app.models.discovery_scan_document import (
        DISCOVERY_DOCUMENT_STATUS_COMPLETED,
        DiscoveryScanDocument,
    )

    _user_id, document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=FakeTextProvider(),
            discovery_engine=FakeDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
        )

        scan = orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])

        tracked = db.query(DiscoveryScanDocument).filter(
            DiscoveryScanDocument.scan_id == scan.id
        ).one()
        assert tracked.document_id == document_id
        assert tracked.status == DISCOVERY_DOCUMENT_STATUS_COMPLETED
        assert tracked.warning_code is None
    finally:
        db.close()


def test_orchestrator_tracks_unsupported_document_as_skipped() -> None:
    _user_id, document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=UnsupportedTextProvider(),
            discovery_engine=FakeDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
        )

        scan = orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])

        assert scan.status == DISCOVERY_SCAN_STATUS_COMPLETED_WITH_WARNINGS
        assert scan.documents_processed == 0
        tracked = db.query(DiscoveryScanDocument).one()
        assert tracked.status == DISCOVERY_DOCUMENT_STATUS_SKIPPED
        assert tracked.warning_code == DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION
        assert db.query(EvidenceFinding).count() == 0
    finally:
        db.close()

    verification_db = SessionLocal()
    try:
        assert verification_db.query(AuditLog).filter(
            AuditLog.event_type == DISCOVERY_DOCUMENT_SKIPPED
        ).count() == 1
        assert verification_db.query(AuditLog).filter(
            AuditLog.event_type == DISCOVERY_COMPLETED
        ).count() == 1
    finally:
        verification_db.close()


def test_orchestrator_tracks_failed_document_without_raw_error() -> None:
    _user_id, document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=FakeTextProvider(),
            discovery_engine=FailingDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
        )

        with pytest.raises(DiscoveryOrchestrationError):
            orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])

        tracked = db.query(DiscoveryScanDocument).one()
        assert tracked.status == DISCOVERY_DOCUMENT_STATUS_FAILED
        assert tracked.warning_code == DISCOVERY_DOCUMENT_WARNING_PROCESSING_FAILED
        assert "sensitive internal failure" not in tracked.warning_code
    finally:
        db.close()


def test_orchestrator_explicitly_persists_checkpoint_audits() -> None:
    _user_id, document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=FakeTextProvider(),
            discovery_engine=FakeDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
        )
        scan = orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])
        scan_id = scan.id
    finally:
        db.close()

    verification_db = SessionLocal()
    try:
        event_types = [
            audit.event_type
            for audit in verification_db.query(AuditLog)
            .filter(AuditLog.user_id == "user-1")
            .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
            .all()
        ]
        assert event_types.count(DISCOVERY_STARTED) == 2
        assert EVIDENCE_FINDING_CREATED in event_types
        assert DISCOVERY_DOCUMENT_COMPLETED in event_types
        assert DISCOVERY_COMPLETED in event_types
        assert verification_db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == scan_id).count() == 1
    finally:
        verification_db.close()


def test_audit_failure_during_document_processing_does_not_persist_partial_findings() -> None:
    _user_id, document_id = _create_user_and_document()
    finding_audits = 0

    def fail_second_finding_audit(db, user_id, event_type, details):
        nonlocal finding_audits
        if event_type == EVIDENCE_FINDING_CREATED:
            finding_audits += 1
            if finding_audits == 2:
                raise RuntimeError("simulated audit failure")

    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=FakeTextProvider(),
            discovery_engine=TwoCandidateDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
            audit_logger=fail_second_finding_audit,
        )

        with pytest.raises(DiscoveryOrchestrationError):
            orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])
    finally:
        db.close()

    verification_db = SessionLocal()
    try:
        scan = verification_db.query(DiscoveryScan).one()
        tracking = verification_db.query(DiscoveryScanDocument).one()
        assert scan.status == DISCOVERY_SCAN_STATUS_FAILED
        assert tracking.status == DISCOVERY_DOCUMENT_STATUS_FAILED
        assert verification_db.query(EvidenceFinding).count() == 0
    finally:
        verification_db.close()


def test_mark_scan_failed_does_not_rollback_the_caller_session(monkeypatch) -> None:
    _user_id, _document_id = _create_user_and_document()
    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=FakeTextProvider(),
            discovery_engine=FakeDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
        )
        scan = orchestrator.create_scan(db, user_id="user-1")
        user = db.query(User).filter(User.id == "user-1").one()
        user.email = "preserved@example.com"
        rollback = Mock(wraps=db.rollback)
        monkeypatch.setattr(db, "rollback", rollback)

        failed_scan = orchestrator.mark_scan_failed(db, scan_id=scan.id, user_id="user-1")

        assert failed_scan is not None
        assert failed_scan.status == DISCOVERY_SCAN_STATUS_FAILED
        rollback.assert_not_called()
    finally:
        db.close()

    verification_db = SessionLocal()
    try:
        assert verification_db.query(User).filter(User.id == "user-1").one().email == "preserved@example.com"
        assert verification_db.query(AuditLog).filter(AuditLog.event_type == DISCOVERY_FAILED).count() == 1
    finally:
        verification_db.close()


def test_unsupported_document_audit_failure_does_not_persist_skipped_state() -> None:
    _user_id, document_id = _create_user_and_document()

    def fail_skipped_audit(db, user_id, event_type, details):
        if event_type == DISCOVERY_DOCUMENT_SKIPPED:
            raise RuntimeError("simulated skipped audit failure")
        log_event(db=db, user_id=user_id, event_type=event_type, details=details)

    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=UnsupportedTextProvider(),
            discovery_engine=FakeDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
            audit_logger=fail_skipped_audit,
        )

        with pytest.raises(DiscoveryOrchestrationError):
            orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])
    finally:
        db.close()

    verification_db = SessionLocal()
    try:
        scan = verification_db.query(DiscoveryScan).one()
        tracking = verification_db.query(DiscoveryScanDocument).one()
        assert scan.status == DISCOVERY_SCAN_STATUS_FAILED
        assert tracking.status != DISCOVERY_DOCUMENT_STATUS_SKIPPED
        assert tracking.warning_code != DISCOVERY_DOCUMENT_WARNING_UNSUPPORTED_EXTRACTION
        assert verification_db.query(AuditLog).filter(AuditLog.event_type == DISCOVERY_DOCUMENT_SKIPPED).count() == 0
        assert verification_db.query(AuditLog).filter(AuditLog.event_type == DISCOVERY_FAILED).count() == 1
    finally:
        verification_db.close()


def test_completion_audit_failure_does_not_persist_complete_state() -> None:
    _user_id, document_id = _create_user_and_document()

    def fail_completion_audit(db, user_id, event_type, details):
        if event_type == DISCOVERY_COMPLETED:
            raise RuntimeError("simulated completion audit failure")
        log_event(db=db, user_id=user_id, event_type=event_type, details=details)

    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(
            text_provider=FakeTextProvider(),
            discovery_engine=FakeDiscoveryEngine(),
            privacy_service=FakePrivacyService(),
            audit_logger=fail_completion_audit,
        )

        with pytest.raises(DiscoveryOrchestrationError):
            orchestrator.run_scan(db, user_id="user-1", document_ids=[document_id])
    finally:
        db.close()

    verification_db = SessionLocal()
    try:
        scan = verification_db.query(DiscoveryScan).one()
        assert scan.status == DISCOVERY_SCAN_STATUS_FAILED
        assert verification_db.query(AuditLog).filter(AuditLog.event_type == DISCOVERY_COMPLETED).count() == 0
        assert verification_db.query(AuditLog).filter(AuditLog.event_type == DISCOVERY_FAILED).count() == 1
        assert verification_db.query(DiscoveryScanDocument).one().status == DISCOVERY_DOCUMENT_STATUS_COMPLETED
        assert verification_db.query(EvidenceFinding).filter(EvidenceFinding.scan_id == scan.id).count() == 1
    finally:
        verification_db.close()


def test_mark_scan_failed_audit_failure_rolls_back_state_and_completion_time() -> None:
    _create_user_and_document()
    setup_db = SessionLocal()
    try:
        scan = DiscoveryOrchestrator().create_scan(setup_db, user_id="user-1")
        scan_id = scan.id
    finally:
        setup_db.close()

    def fail_failure_audit(db, user_id, event_type, details):
        if event_type == DISCOVERY_FAILED:
            raise RuntimeError("simulated failure audit failure")
        log_event(db=db, user_id=user_id, event_type=event_type, details=details)

    db = SessionLocal()
    try:
        orchestrator = DiscoveryOrchestrator(audit_logger=fail_failure_audit)
        with pytest.raises(RuntimeError, match="simulated failure audit failure"):
            orchestrator.mark_scan_failed(db, scan_id=scan_id, user_id="user-1")
    finally:
        db.close()

    verification_db = SessionLocal()
    try:
        persisted_scan = verification_db.query(DiscoveryScan).filter(DiscoveryScan.id == scan_id).one()
        assert persisted_scan.status == DISCOVERY_SCAN_STATUS_PENDING
        assert persisted_scan.completed_at is None
        assert verification_db.query(AuditLog).filter(AuditLog.event_type == DISCOVERY_FAILED).count() == 0
    finally:
        verification_db.close()
