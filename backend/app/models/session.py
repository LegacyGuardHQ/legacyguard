from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.sql import func

from app.database.connection import Base


class UserSession(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    token_identifier = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    device_info = Column(Text, nullable=True)
