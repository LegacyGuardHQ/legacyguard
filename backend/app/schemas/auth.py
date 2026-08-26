from datetime import datetime

from pydantic import BaseModel, Field, field_validator


BCRYPT_MAX_PASSWORD_BYTES = 72


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 12:
            raise ValueError("Password must be at least 12 characters long")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must include at least one uppercase letter")
        if not any(char.islower() for char in value):
            raise ValueError("Password must include at least one lowercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must include at least one number")
        if not any(char in "!@#$%^&*()-_=+[]{};:'\",.<>/?" for char in value):
            raise ValueError("Password must include at least one special character")
        if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None
