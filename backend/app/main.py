import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from starlette.responses import Response

from app.api.asset_beneficiaries import router as asset_beneficiaries_router
from app.api.assets import router as assets_router
from app.api.auth import router as auth_router
from app.api.beneficiaries import router as beneficiaries_router
from app.api.discovery import router as discovery_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.config import get_settings, settings
from app.services.encryption import validate_encryption_key
from app.services.operational_logging import log_event
from app.version import __version__


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Validate startup configuration without mutating the database schema.

    Database schema changes are owned exclusively by Alembic migrations. This
    prevents application imports or startup from creating tables/columns ahead
    of the migration history.
    """
    log_event("startup_begin", event_category="startup", severity="info")
    runtime_settings = get_settings()
    try:
        validate_encryption_key(runtime_settings.encryption_key)
    except Exception as exc:
        log_event("startup_config_failed", event_category="startup", severity="error", reason="configuration_validation_failed")
        raise
    log_event("startup_complete", event_category="startup", severity="info")
    yield
    log_event("shutdown", event_category="shutdown", severity="info")


logging.basicConfig(level=logging.INFO)
logging.getLogger("legacyguard").setLevel(logging.INFO)

app = FastAPI(
    title="LegacyGuard",
    description="Secure personal asset continuity and legacy planning system",
    version=__version__,
    lifespan=lifespan,
)

@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    runtime_settings = get_settings()
    origin = request.headers.get("origin")

    if origin and origin in runtime_settings.cors_origins:
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
            response.headers["vary"] = "Origin"
            response.headers["access-control-allow-methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["access-control-max-age"] = "600"
            requested_headers = request.headers.get("access-control-request-headers")
            response.headers["access-control-allow-headers"] = requested_headers or "Authorization, Content-Type"
            return response

        response = await call_next(request)
        response.headers["access-control-allow-origin"] = origin
        response.headers["access-control-allow-credentials"] = "true"
        response.headers["vary"] = "Origin"
        return response

    if request.method == "OPTIONS" and origin:
        return Response(status_code=400)

    return await call_next(request)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(assets_router)
app.include_router(asset_beneficiaries_router)
app.include_router(beneficiaries_router)
app.include_router(documents_router)
app.include_router(discovery_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "LegacyGuard API is running"}
