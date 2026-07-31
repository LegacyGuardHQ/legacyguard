import os
from unittest.mock import Mock

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.database.connection import Base, SessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.audit import log_event


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_log_event_is_transaction_neutral() -> None:
    db = Mock()

    log_event(
        db,
        user_id="user-1",
        event_type="TEST_EVENT",
        details="Safe audit details",
    )

    db.add.assert_called_once()
    db.flush.assert_called_once_with()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()
    db.close.assert_not_called()


def test_business_mutation_and_audit_can_be_rolled_back_together() -> None:
    db = SessionLocal()
    try:
        db.add(User(id="rollback-user", email="rollback@example.com", password_hash="hash"))
        log_event(
            db,
            user_id="rollback-user",
            event_type="TEST_ROLLBACK",
            details="Rollback transaction",
        )
        db.rollback()
    finally:
        db.close()

    verification_db = SessionLocal()
    try:
        assert verification_db.query(User).filter(User.id == "rollback-user").count() == 0
        assert verification_db.query(AuditLog).filter(AuditLog.event_type == "TEST_ROLLBACK").count() == 0
    finally:
        verification_db.close()


def test_business_mutation_and_sanitized_audit_persist_after_caller_commit() -> None:
    db = SessionLocal()
    try:
        db.add(User(id="commit-user", email="commit@example.com", password_hash="hash"))
        log_event(
            db,
            user_id="commit-user",
            event_type="TEST_COMMIT",
            details="Commit transaction",
            metadata={
                "resource_type": "user",
                "resource_id": "commit-user",
                "document_text": "must not persist",
            },
        )
        db.commit()
    finally:
        db.close()

    verification_db = SessionLocal()
    try:
        assert verification_db.query(User).filter(User.id == "commit-user").one()
        audit = verification_db.query(AuditLog).filter(AuditLog.event_type == "TEST_COMMIT").one()
        assert audit.event_metadata == {
            "resource_type": "user",
            "resource_id": "commit-user",
        }
        assert "must not persist" not in str(audit.event_metadata)
    finally:
        verification_db.close()
