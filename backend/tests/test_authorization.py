import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.models.asset import Asset
from app.models.beneficiary import Beneficiary
from app.models.document import Document
from app.models.report import Report
from app.models.task import Task
from app.models.user import User
from app.security.authorization import ensure_owner, get_owned_query, get_owned_record
from app.services.ownership import apply_audit_user, assign_owner, can_access_record, is_record_owner


@pytest.fixture(autouse=True)
def reset_db() -> None:
    from app.database.connection import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _users() -> tuple[User, User]:
    return (
        User(id="user-a", email="a@example.com", password_hash="hash", role="USER"),
        User(id="user-b", email="b@example.com", password_hash="hash", role="USER"),
    )


def test_user_can_access_owned_asset_and_not_other_users_asset(db_session) -> None:
    user_a, user_b = _users()
    asset_a = Asset(id="asset-a", user_id=user_a.id, asset_category="Bank", asset_name="Checking", status="Active")
    asset_b = Asset(id="asset-b", user_id=user_b.id, asset_category="Bank", asset_name="Savings", status="Active")
    db_session.add_all([user_a, user_b, asset_a, asset_b])
    db_session.commit()

    assert get_owned_record(db_session, Asset, "asset-a", user_a).id == "asset-a"

    with pytest.raises(HTTPException) as exc:
        get_owned_record(db_session, Asset, "asset-b", user_a)

    assert exc.value.status_code == 404


def test_owned_query_returns_only_current_user_records(db_session) -> None:
    user_a, user_b = _users()
    db_session.add_all(
        [
            user_a,
            user_b,
            Beneficiary(id="ben-a", user_id=user_a.id, name="A Beneficiary"),
            Beneficiary(id="ben-b", user_id=user_b.id, name="B Beneficiary"),
        ]
    )
    db_session.commit()

    records = get_owned_query(db_session, Beneficiary, user_a).all()

    assert [record.id for record in records] == ["ben-a"]


def test_ownership_utilities_support_create_update_delete_policy() -> None:
    user = User(id="user-a", email="a@example.com", password_hash="hash", role="USER")
    document = Document(id="doc-a", document_type="Will", document_name="Will.pdf")

    assign_owner(document, user.id)
    apply_audit_user(document, user.id, is_create=True)

    assert document.user_id == user.id
    assert document.created_by == user.id
    assert document.modified_by == user.id
    assert can_access_record(document.user_id, user.id) is True
    assert is_record_owner(document, user.id) is True


def test_user_cannot_access_other_owned_resource_types() -> None:
    user_a = User(id="user-a", email="a@example.com", password_hash="hash", role="USER")
    user_b = User(id="user-b", email="b@example.com", password_hash="hash", role="USER")
    resources = [
        Beneficiary(id="ben-b", user_id=user_b.id, name="B Beneficiary"),
        Document(id="doc-b", user_id=user_b.id, document_type="Will", document_name="Will.pdf"),
        Report(id="report-b", user_id=user_b.id, report_type="Summary"),
        Task(id="task-b", user_id=user_b.id, task_name="Review"),
    ]

    for resource in resources:
        with pytest.raises(HTTPException) as exc:
            ensure_owner(resource, user_a)
        assert exc.value.status_code == 404