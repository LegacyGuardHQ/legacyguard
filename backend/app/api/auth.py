import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.models.session import UserSession
from app.models.user import User
from app.models.user_security_settings import UserSecuritySettings
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.config import settings
from app.security.auth import create_access_token, create_refresh_token, get_current_user, get_db, get_password_hash, verify_password
from app.services.audit import log_event
from app.services.rate_limit import rate_limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db), request: Request = None) -> User:
    existing = db.query(User).filter(User.email == str(payload.email).lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=str(payload.email).lower(),
        password_hash=get_password_hash(payload.password),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        role="USER",
    )
    settings = UserSecuritySettings(user_id=user.id, mfa_enabled=False, mfa_method=None, recovery_codes=None, security_preferences="{}")
    db.add(user)
    db.add(settings)
    db.commit()
    db.refresh(user)

    log_event(db=db, user_id=user.id, event_type="ACCOUNT_CREATED", details="User registered", request=request)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db), request: Request = None) -> dict[str, str]:
    client_key = request.client.host if request and request.client else "unknown"
    allowed, retry_after = rate_limiter.allow(client_key)
    if not allowed:
        log_event(db=db, user_id=None, event_type="LOGIN_FAILED", details="Rate limited", request=request)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts")

    user = db.query(User).filter(User.email == str(payload.email).lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        log_event(db=db, user_id=user.id if user else None, event_type="LOGIN_FAILED", details="Invalid credentials", request=request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    user.last_login = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)

    session_id = str(uuid.uuid4())
    token_identifier = str(uuid.uuid4())
    session = UserSession(
        id=session_id,
        user_id=user.id,
        token_identifier=token_identifier,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        revoked_at=None,
        device_info=str(request.headers.get("user-agent", "unknown")) if request else "unknown",
    )
    db.add(session)
    db.commit()

    log_event(db=db, user_id=user.id, event_type="LOGIN_SUCCESS", details="User logged in", request=request)
    return {
        "access_token": create_access_token(user.id, token_identifier),
        "refresh_token": create_refresh_token(user.id, token_identifier),
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    token_identifier = current_user.current_token_identifier if hasattr(current_user, "current_token_identifier") else None
    if token_identifier:
        session = db.query(UserSession).filter(UserSession.user_id == current_user.id, UserSession.token_identifier == token_identifier).first()
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
    log_event(db=db, user_id=current_user.id, event_type="LOGOUT", details="User logged out", request=None)
    return {"message": "Logout successful"}


@router.post("/sessions/revoke-all")
def revoke_all_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    db.query(UserSession).filter(UserSession.user_id == current_user.id).update({"revoked_at": datetime.now(timezone.utc)})
    db.commit()
    log_event(db=db, user_id=current_user.id, event_type="SESSION_REVOKED", details="All sessions revoked", request=None)
    return {"message": "All sessions revoked"}


@router.get("/sessions")
def list_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Optional[str]]]:
    sessions = db.query(UserSession).filter(UserSession.user_id == current_user.id).all()
    return [
        {
            "id": session.id,
            "token_identifier": session.token_identifier,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "revoked_at": session.revoked_at.isoformat() if session.revoked_at else None,
            "device_info": session.device_info,
        }
        for session in sessions
    ]


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
