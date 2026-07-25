from sqlalchemy import JSON, Column, DateTime, String, Text
from sqlalchemy.sql import func

from app.database.connection import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    # ``metadata`` is reserved by SQLAlchemy's declarative API, so the Python
    # attribute uses a safe name while the database column remains "metadata".
    event_metadata = Column("metadata", JSON, nullable=True)
