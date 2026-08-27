import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.api.documents import MAX_DOCUMENTS_PER_USER, create_document_metadata
from app.database.connection import Base
from app.models.discovery import DiscoveryScan
from app.models.document import DOCUMENT_STATUS_ACTIVE, DOCUMENT_VERIFICATION_UNKNOWN, Document
from app.models.user import User
from app.schemas.documents import DocumentCreate
from app.services.discovery_orchestrator import DiscoveryScanExecutor, DiscoveryUserScanLimitError, DiscoveryOrchestrator


def _sqlite_session_factory(database_path: Path):
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine), engine


def _seed_user_with_documents(session_factory, *, count: int) -> str:
    db = session_factory()
    try:
        user_id = "concurrent-user"
        db.add(User(id=user_id, email="concurrent@example.com", password_hash="not-used"))
        db.add_all(
            [
                Document(
                    id=f"existing-{index}",
                    user_id=user_id,
                    document_type="WILL",
                    document_name=f"Existing {index}",
                    status=DOCUMENT_STATUS_ACTIVE,
                    verification_status=DOCUMENT_VERIFICATION_UNKNOWN,
                    version_number=1,
                )
                for index in range(count)
            ]
        )
        db.commit()
        return user_id
    finally:
        db.close()


def test_sqlite_document_quota_is_atomic_across_separate_sessions(tmp_path: Path) -> None:
    for attempt in range(5):
        session_factory, engine = _sqlite_session_factory(tmp_path / f"document-quota-{attempt}.db")
        try:
            user_id = _seed_user_with_documents(session_factory, count=MAX_DOCUMENTS_PER_USER - 1)
            start = Barrier(2)

            def create_document(index: int) -> tuple[int, str]:
                db = session_factory()
                try:
                    current_user = db.query(User).filter(User.id == user_id).one()
                    start.wait(timeout=5)
                    create_document_metadata(
                        DocumentCreate(document_type="WILL", document_name=f"Concurrent {index}"),
                        current_user=current_user,
                        db=db,
                    )
                    return 201, ""
                except HTTPException as exc:
                    return exc.status_code, exc.detail
                finally:
                    db.close()

            with ThreadPoolExecutor(max_workers=2) as executor:
                statuses = sorted(executor.map(create_document, range(2)))

            verification_db = session_factory()
            try:
                assert statuses == [(201, ""), (409, "Document limit reached.")]
                assert verification_db.query(Document).filter(Document.user_id == user_id).count() == MAX_DOCUMENTS_PER_USER
            finally:
                verification_db.close()
        finally:
            engine.dispose()


def test_sqlite_active_scan_limit_is_atomic_across_separate_sessions(tmp_path: Path) -> None:
    for attempt in range(5):
        session_factory, engine = _sqlite_session_factory(tmp_path / f"discovery-scan-{attempt}.db")
        try:
            user_id = _seed_user_with_documents(session_factory, count=0)
            executor = DiscoveryScanExecutor(DiscoveryOrchestrator(stale_scan_threshold_seconds=None))
            start = Barrier(2)

            def create_scan() -> str:
                db = session_factory()
                try:
                    start.wait(timeout=5)
                    return executor.create_pending_bounded(db, user_id=user_id).id
                except DiscoveryUserScanLimitError:
                    return "limited"
                finally:
                    db.close()

            with ThreadPoolExecutor(max_workers=2) as thread_pool:
                results = list(thread_pool.map(lambda _index: create_scan(), range(2)))

            assert results.count("limited") == 1
            executor.release_pending_slot()
            verification_db = session_factory()
            try:
                assert verification_db.query(DiscoveryScan).filter(DiscoveryScan.user_id == user_id).count() == 1
            finally:
                verification_db.close()
        finally:
            engine.dispose()
