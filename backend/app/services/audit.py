from datetime import datetime, timezone
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_event(
    db: Session,
    *,
    user_id: Optional[str],
    event_type: str,
    details: str,
    request: Optional[Request] = None,
) -> None:
    ip_address = None
    if request is not None:
        ip_address = request.client.host if request.client else None

    audit_entry = AuditLog(
        id=str(__import__("uuid").uuid4()),
        user_id=user_id,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        ip_address=ip_address,
        details=details,
    )
    db.add(audit_entry)
    db.commit()
