from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import SessionLocal
from app.models.session import UserSession
from app.models.user import User

security = HTTPBearer(auto_error=False)
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_context.hash(password)


def hash_password(password: str) -> str:
    return get_password_hash(password)


def _get_token_identifier(token_identifier: Optional[str] = None) -> str:
    return token_identifier or str(uuid.uuid4())


def _create_token(subject: str, expires_delta: timedelta, token_identifier: Optional[str] = None, token_type: str = "access") -> str:
    now = datetime.now(timezone.utc)
    resolved_token_identifier = _get_token_identifier(token_identifier)
    payload = {
        "sub": subject,
        "exp": now + expires_delta,
        "iat": now,
        "jti": resolved_token_identifier,
        "typ": token_type,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_access_token(subject: str, token_identifier: Optional[str] = None) -> str:
    return _create_token(
        subject=subject,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        token_identifier=token_identifier,
        token_type="access",
    )


def create_refresh_token(subject: str, token_identifier: Optional[str] = None) -> str:
    return _create_token(
        subject=subject,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        token_identifier=token_identifier,
        token_type="refresh",
    )


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("typ") not in (None, "access"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    token_identifier = payload.get("jti")
    if not token_identifier:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    session = db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.token_identifier == token_identifier).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalid")

    revoked_at = _normalize_datetime(session.revoked_at)
    expires_at = _normalize_datetime(session.expires_at)
    if revoked_at is not None or expires_at is None or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalid")

    user.current_token_identifier = token_identifier
    return user
