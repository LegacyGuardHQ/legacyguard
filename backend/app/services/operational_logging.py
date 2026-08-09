import logging
import re
from collections.abc import Mapping
from typing import Any

logger = logging.getLogger("legacyguard")

_REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = {
    "authorization",
    "authorizationheader",
    "password",
    "passwd",
    "secret",
    "secret_key",
    "jwt",
    "jwt_secret",
    "encryption_key",
    "token",
    "refresh_token",
    "access_token",
    "api_key",
    "apikey",
}


def _should_redact(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "", key.lower())
    return normalized in _SENSITIVE_KEYS or any(part in normalized for part in ("password", "token", "secret", "authorization"))


def sanitize_for_logging(value: Any, *, depth: int = 0) -> Any:
    if depth > 3:
        return _REDACTED

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if _should_redact(str(key)):
                result[str(key)] = _REDACTED
            else:
                result[str(key)] = sanitize_for_logging(item, depth=depth + 1)
        return result

    if isinstance(value, (list, tuple, set)):
        return [sanitize_for_logging(item, depth=depth + 1) for item in value]

    if isinstance(value, str):
        if depth == 0 and value:
            return value
        return value

    return value


def log_event(event: str, *, level: int = logging.INFO, **metadata: Any) -> None:
    logger.log(level, "event=%s %s", event, sanitize_for_logging(metadata))
