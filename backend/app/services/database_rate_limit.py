from __future__ import annotations

import hashlib
import math
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.connection import begin_serialized_write
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

    def _evaluate(self, db: Session, key: str) -> tuple[bool, int]:
        now = datetime.now(timezone.utc)
        attempts = (
            db.query(LoginRateLimitAttempt)
            .filter(
                LoginRateLimitAttempt.client_key_hash == self._hash_key(key),
                LoginRateLimitAttempt.attempted_at
                >= now - timedelta(seconds=self.window_seconds + self.lockout_seconds),
            )
            .order_by(LoginRateLimitAttempt.attempted_at.desc())
            .limit(self.max_attempts)
            .all()
        )
        if len(attempts) < self.max_attempts:
            return True, 0

        newest = self._aware(attempts[0].attempted_at)
        oldest = self._aware(attempts[-1].attempted_at)
        if newest - oldest > timedelta(seconds=self.window_seconds):
            return True, 0

        locked_until = newest + timedelta(seconds=self.lockout_seconds)
        if now >= locked_until:
            return True, 0
        return False, max(1, math.ceil((locked_until - now).total_seconds()))

    def allow(self, db: Session, key: str) -> tuple[bool, int]:
        return self._evaluate(db, key)

    def record_attempt(self, db: Session, key: str) -> None:
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

    def record_failure(self, db: Session, key: str) -> None:
        self.record_attempt(db, key)

    def _acquire_transaction_lock(self, db: Session, key: str) -> None:
        dialect = db.get_bind().dialect.name
        if dialect == "sqlite":
            begin_serialized_write(db)
        elif dialect == "postgresql":
            digest = bytes.fromhex(self._hash_key(key))
            lock_key = int.from_bytes(digest[:8], byteorder="big", signed=True)
            db.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": lock_key})

    def record_and_allow(self, db: Session, key: str) -> tuple[bool, int]:
        """Serialize check-and-record for a client key across supported workers."""
        self._acquire_transaction_lock(db, key)
        allowed, retry_after = self.allow(db, key)
        if allowed:
            self.record_attempt(db, key)
        db.commit()
        return allowed, retry_after


database_login_rate_limiter = DatabaseLoginRateLimiter()
database_registration_rate_limiter = DatabaseLoginRateLimiter()
