from __future__ import annotations

import hashlib
import math
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.login_rate_limit_attempt import LoginRateLimitAttempt


class DatabaseLoginRateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300, lockout_seconds: int = 900) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    def allow(self, db: Session, key: str) -> tuple[bool, int]:
        now = datetime.now(timezone.utc)
        failures = (
            db.query(LoginRateLimitAttempt)
            .filter(
                LoginRateLimitAttempt.client_key_hash == self._hash_key(key),
                LoginRateLimitAttempt.attempted_at >= now - timedelta(seconds=self.window_seconds),
            )
            .order_by(LoginRateLimitAttempt.attempted_at.desc())
            .limit(self.max_attempts)
            .all()
        )
        if len(failures) < self.max_attempts:
            return True, 0

        locked_until = self._aware(failures[0].attempted_at) + timedelta(seconds=self.lockout_seconds)
        if now >= locked_until:
            return True, 0
        return False, max(1, math.ceil((locked_until - now).total_seconds()))

    def record_failure(self, db: Session, key: str) -> None:
        now = datetime.now(timezone.utc)
        key_hash = self._hash_key(key)
        retention_cutoff = now - timedelta(seconds=self.window_seconds + self.lockout_seconds)
        db.query(LoginRateLimitAttempt).filter(
            LoginRateLimitAttempt.client_key_hash == key_hash,
            LoginRateLimitAttempt.attempted_at < retention_cutoff,
        ).delete(synchronize_session=False)
        db.add(
            LoginRateLimitAttempt(
                id=str(uuid.uuid4()),
                client_key_hash=key_hash,
                attempted_at=now,
            )
        )
        db.flush()


database_login_rate_limiter = DatabaseLoginRateLimiter()
