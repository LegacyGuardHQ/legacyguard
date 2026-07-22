from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.asset_beneficiaries import router as asset_beneficiaries_router
from app.api.assets import router as assets_router
from app.api.auth import router as auth_router
from app.api.beneficiaries import router as beneficiaries_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.config import settings
from app.database.connection import init_db
from app.services.encryption import validate_encryption_key

validate_encryption_key(settings.encryption_key)

app = FastAPI(
    title="LegacyGuard",
    description="Secure personal asset continuity and legacy planning system",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(assets_router)
app.include_router(asset_beneficiaries_router)
app.include_router(beneficiaries_router)
app.include_router(documents_router)

init_db()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "LegacyGuard API is running"}
