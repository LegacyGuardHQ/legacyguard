from sqlalchemy import Boolean, Column, String, Text
from app.database.connection import Base


class UserSecuritySettings(Base):
    __tablename__ = "user_security_settings"

    user_id = Column(String, primary_key=True, index=True)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_method = Column(String, nullable=True)
    recovery_codes = Column(Text, nullable=True)
    security_preferences = Column(Text, nullable=True)
