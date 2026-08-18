import re

from pydantic import ValidationError, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_ENCRYPTION_KEY = "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE="
MIN_SECRET_LENGTH = 24
DEFAULT_DEV_SECRET_KEYS = {"legacyguard-dev-secret-key-123456", "dev-secret-key-123456"}
DEFAULT_DEV_JWT_SECRETS = {"legacyguard-dev-jwt-secret-123456", "dev-jwt-secret-123456"}


class Settings(BaseSettings):
    app_name: str = "LegacyGuard"
    debug: bool = False
    database_url: str = "sqlite:///./legacyguard.db"
    secret_key: str = "legacyguard-dev-secret-key-123456"
    encryption_key: str = DEV_ENCRYPTION_KEY
    jwt_secret: str = "legacyguard-dev-jwt-secret-123456"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    environment: str = "development"
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    document_storage_root: str | None = None
    discovery_stale_scan_threshold_seconds: int | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_required_keys(self) -> "Settings":
        normalized_environment = self.environment.lower()
        self.environment = normalized_environment

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
            if self.database_url.startswith("sqlite:///:memory:"):
                raise ValueError("production database_url must not use an in-memory database")

        if normalized_environment in {"production", "staging"}:
            if not re.search(r"[A-Za-z]", self.secret_key) or not re.search(r"\d", self.secret_key):
                raise ValueError("secret_key must include letters and digits")
            if not re.search(r"[A-Za-z]", self.jwt_secret) or not re.search(r"\d", self.jwt_secret):
                raise ValueError("jwt_secret must include letters and digits")

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
