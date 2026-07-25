from datetime import datetime, timezone
from typing import Any, Mapping, Optional
import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

_ALLOWED_METADATA_KEYS = {
    "resource_type",
    "resource_id",
    "event_type",
    "old_status",
    "new_status",
    "scan_id",
    "document_id",
    "discovery_scan_document_id",
    "finding_id",
}


def _sanitize_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Return a small, non-sensitive audit metadata payload.

    Unknown keys are discarded rather than persisted. Values are limited to
    scalar identifiers/status values so document content, evidence, filenames,
    user input, and nested arbitrary data cannot enter the audit log.
    """
    if not metadata:
        return None

    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        if key not in _ALLOWED_METADATA_KEYS or value is None:
            continue
        if isinstance(value, uuid.UUID):
            sanitized[key] = str(value)
        elif isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
    return sanitized or None


def log_event(
    db: Session,
    *,
    user_id: Optional[str],
    event_type: str,
    details: str,
    request: Optional[Request] = None,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    ip_address = None
    if request is not None:
        ip_address = request.client.host if request.client else None

    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        ip_address=ip_address,
        details=details,
        event_metadata=_sanitize_metadata(metadata),
    )
    db.add(audit_entry)
    db.commit()
