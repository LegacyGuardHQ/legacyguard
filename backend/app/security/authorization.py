from typing import Any, Callable, TypeVar

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.security.auth import get_current_user, get_db
from app.services.ownership import filter_by_owner, is_record_owner

OwnedRecord = TypeVar("OwnedRecord")


def require_authenticated_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def ensure_owner(record: OwnedRecord | None, current_user: User) -> OwnedRecord:
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    if not is_record_owner(record, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return record


def get_owned_record(db: Session, model: type[OwnedRecord], record_id: str, current_user: User) -> OwnedRecord:
    record = db.query(model).filter(model.id == record_id).first()
    return ensure_owner(record, current_user)


def get_owned_query(db: Session, model: type[Any], current_user: User):
    return filter_by_owner(db.query(model), current_user.id)


def owned_record_dependency(model: type[OwnedRecord], id_param: str = "record_id") -> Callable[..., OwnedRecord]:
    def dependency(
        record_id: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> OwnedRecord:
        return get_owned_record(db, model, record_id, current_user)

    dependency.__name__ = f"get_owned_{model.__name__.lower()}"
    return dependency