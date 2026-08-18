from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from app.database.connection import Base


class LoginRateLimitAttempt(Base):
    __tablename__ = "login_rate_limit_attempts"

    id = Column(String, primary_key=True)
    client_key_hash = Column(String(64), nullable=False, index=True)
    attempted_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
