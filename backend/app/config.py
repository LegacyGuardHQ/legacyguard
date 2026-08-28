import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, ValidationError, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.database.url import normalize_database_url

DEV_ENCRYPTION_KEY = "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE="
MIN_SECRET_LENGTH = 24
DEFAULT_DEV_SECRET_KEYS = {"legacyguard-dev-secret-key-123456", "dev-secret-key-123456"}
DEFAULT_DEV_JWT_SECRETS = {"legacyguard-dev-jwt-secret-123456", "dev-jwt-secret-123456"}


class Settings(BaseSettings):
    app_name: str = "LegacyGuard"
    debug: bool = False
    database_url: str = "sqlite:///./legacyguard.db"
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    database_pool_timeout_seconds: int = Field(default=30, ge=1)
    database_pool_recycle_seconds: int = Field(default=1800, ge=1)
    secret_key: str = "legacyguard-dev-secret-key-123456"
    encryption_key: str = DEV_ENCRYPTION_KEY
    jwt_secret: str = "legacyguard-dev-jwt-secret-123456"
    access_token_expire_minutes: int = 15
    environment: Literal["development", "testing", "staging", "production"] = "development"
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    document_storage_root: str | None = None
    document_storage_backend: str = Field(default="LOCAL", pattern=r"^(LOCAL|OBJECT)$")
    document_object_bucket: str | None = Field(default=None, min_length=3, max_length=63)
    document_object_prefix: str = Field(default="legacyguard", max_length=256)
    document_object_region: str | None = Field(default=None, max_length=64)
    document_object_endpoint_url: str | None = None
    document_object_access_key_id: str | None = None
    document_object_secret_access_key: str | None = None
    document_object_session_token: str | None = None
    document_object_addressing_style: str = Field(default="auto", pattern=r"^(auto|virtual|path)$")
    document_object_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    document_object_read_timeout_seconds: int = Field(default=30, ge=1, le=300)
    document_object_max_attempts: int = Field(default=3, ge=1, le=10)
    document_master_key_id: str = Field(default="legacy-current-v1", pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    discovery_stale_scan_threshold_seconds: int = Field(default=900, ge=60, le=86_400)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @model_validator(mode="after")
    def validate_required_keys(self) -> "Settings":
        normalized_environment = self.environment
        self.document_storage_backend = self.document_storage_backend.upper()

        if normalized_environment != "testing":
            for field_name in ("secret_key", "encryption_key", "jwt_secret"):
                value = getattr(self, field_name)
                if not value:
                    raise ValueError(f"{field_name} is required")
            if self.encryption_key == DEV_ENCRYPTION_KEY:
                raise ValueError("encryption_key must be explicitly configured outside testing")
            if self.secret_key in DEFAULT_DEV_SECRET_KEYS or len(self.secret_key) < MIN_SECRET_LENGTH:
                raise ValueError("secret_key must be at least 24 characters and must not use a default value")
            if self.jwt_secret in DEFAULT_DEV_JWT_SECRETS or len(self.jwt_secret) < MIN_SECRET_LENGTH:
                raise ValueError("jwt_secret must be at least 24 characters and must not use a default value")

        if normalized_environment == "production":
            if self.debug:
                raise ValueError("debug must be false in production")
            if self.cors_origins and "*" in self.cors_origins:
                raise ValueError("Wildcard CORS origins are not allowed")
            if not self.cors_origins:
                raise ValueError("cors_allowed_origins must be configured in production")
            if not normalize_database_url(self.database_url).startswith("postgresql+psycopg://"):
                raise ValueError("production database_url must use PostgreSQL with the psycopg driver")
            if self.document_storage_backend != "OBJECT":
                raise ValueError("production document_storage_backend must be OBJECT")

        if normalized_environment in {"production", "staging"}:
            if not re.search(r"[A-Za-z]", self.secret_key) or not re.search(r"\d", self.secret_key):
                raise ValueError("secret_key must include letters and digits")
            if not re.search(r"[A-Za-z]", self.jwt_secret) or not re.search(r"\d", self.jwt_secret):
                raise ValueError("jwt_secret must include letters and digits")

        if self.document_storage_backend == "OBJECT":
            if self.document_object_bucket is None:
                raise ValueError("document_object_bucket is required for OBJECT storage")
            if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*[a-z0-9]", self.document_object_bucket):
                raise ValueError("document_object_bucket must be a valid S3-compatible bucket name")
            normalized_prefix = self.document_object_prefix.strip("/")
            if not normalized_prefix or any(
                not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", part) or part in {".", ".."}
                for part in normalized_prefix.split("/")
            ):
                raise ValueError("document_object_prefix must be a safe object-key prefix")
            self.document_object_prefix = normalized_prefix

            explicit_credentials = (
                self.document_object_access_key_id,
                self.document_object_secret_access_key,
            )
            if any(explicit_credentials) and not all(explicit_credentials):
                raise ValueError("object access key id and secret access key must be configured together")
            if self.document_object_session_token and not all(explicit_credentials):
                raise ValueError("object session token requires explicit access key credentials")

            if self.document_object_endpoint_url:
                endpoint = urlsplit(self.document_object_endpoint_url)
                if endpoint.scheme not in {"http", "https"} or not endpoint.hostname:
                    raise ValueError("document_object_endpoint_url must be an absolute HTTP(S) URL")
                if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
                    raise ValueError("document_object_endpoint_url must not contain credentials, query, or fragment")
                if normalized_environment in {"production", "staging"} and endpoint.scheme != "https":
                    raise ValueError("object storage endpoint must use HTTPS outside development/testing")

        return self

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_allowed_origins.split(",") if origin.strip()]


def get_settings() -> Settings:
    return Settings()


try:
    settings = get_settings()
except ValidationError as exc:
    raise RuntimeError(f"Invalid environment configuration: {exc}") from exc
