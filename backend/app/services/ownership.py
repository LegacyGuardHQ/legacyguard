from typing import Any, TypeVar

from sqlalchemy.orm import Query

OwnedRecord = TypeVar("OwnedRecord")


def can_access_record(owner_id: str, requester_id: str) -> bool:
    return owner_id == requester_id


def filter_by_owner(query: Query[Any], user_id: str) -> Query[Any]:
    return query.filter_by(user_id=user_id)


def get_record_owner_id(record: Any) -> str | None:
    return getattr(record, "user_id", None)


def is_record_owner(record: Any, requester_id: str) -> bool:
    owner_id = get_record_owner_id(record)
    return owner_id is not None and can_access_record(owner_id, requester_id)


def assign_owner(record: OwnedRecord, user_id: str) -> OwnedRecord:
    setattr(record, "user_id", user_id)
    return record


def apply_audit_user(record: OwnedRecord, user_id: str, *, is_create: bool = False) -> OwnedRecord:
    if is_create and hasattr(record, "created_by"):
        setattr(record, "created_by", user_id)
    if hasattr(record, "modified_by"):
        setattr(record, "modified_by", user_id)
    return record
