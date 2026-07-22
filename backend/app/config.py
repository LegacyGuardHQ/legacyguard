from pydantic import ValidationError, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_ENCRYPTION_KEY = "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE="


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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_required_keys(self) -> "Settings":
        if self.environment != "testing":
            for field_name in ("secret_key", "encryption_key", "jwt_secret"):
                if not getattr(self, field_name):
                    raise ValueError(f"{field_name} is required")
        if self.environment == "production" and self.encryption_key == DEV_ENCRYPTION_KEY:
            raise ValueError("production encryption_key must be explicitly configured")
        if self.environment == "production" and not self.cors_origins:
            raise ValueError("cors_allowed_origins must be configured in production")
        if "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origins are not allowed")
        return self

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_allowed_origins.split(",") if origin.strip()]


try:
    settings = Settings()
except ValidationError as exc:
    raise RuntimeError(f"Invalid environment configuration: {exc}") from exc
