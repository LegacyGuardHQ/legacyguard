from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Deque, DefaultDict


class RateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300, lockout_seconds: int = 900) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._attempts: DefaultDict[str, Deque[datetime]] = defaultdict(deque)
        self._lockouts: DefaultDict[str, datetime] = defaultdict(datetime)
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = datetime.now(timezone.utc)
        with self._lock:
            lockout_until = self._lockouts.get(key)
            if lockout_until and now < lockout_until:
                return False, int((lockout_until - now).total_seconds())

            window_start = now - timedelta(seconds=self.window_seconds)
            attempts = self._attempts[key]
            while attempts and attempts[0] < window_start:
                attempts.popleft()

            if len(attempts) >= self.max_attempts:
                self._lockouts[key] = now + timedelta(seconds=self.lockout_seconds)
                return False, self.lockout_seconds

            attempts.append(now)
            return True, 0

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
            self._lockouts.pop(key, None)

    def reset_all(self) -> None:
        with self._lock:
            self._attempts.clear()
            self._lockouts.clear()


rate_limiter = RateLimiter()
