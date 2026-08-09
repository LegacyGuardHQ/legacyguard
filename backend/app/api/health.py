from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database.connection import SessionLocal
from app.services.document_storage import LocalDocumentStorage
from app.services.operational_logging import log_event

router = APIRouter()

document_storage = LocalDocumentStorage(settings.document_storage_root or "private_storage/documents")


def check_database_ready() -> bool:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        log_event("ready_check_failed", event_category="health", severity="warning", dependency="database")
        return False


def check_storage_ready() -> bool:
    try:
        document_storage.exists("00000000-0000-0000-0000-000000000000")
        return True
    except Exception:
        log_event("ready_check_failed", event_category="health", severity="warning", dependency="storage")
        return False


def check_migration_ready() -> bool:
    return True


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "application": "LegacyGuard",
    }


@router.get("/health/live", status_code=status.HTTP_200_OK)
def live_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready_check() -> JSONResponse:
    checks: dict[str, str] = {
        "database": "ok" if check_database_ready() else "failed",
        "storage": "ok" if check_storage_ready() else "failed",
        "migrations": "ok" if check_migration_ready() else "failed",
    }
    if all(value == "ok" for value in checks.values()):
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok", "checks": checks})
    log_event("ready_check_degraded", event_category="health", severity="warning", checks=checks)
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "degraded", "checks": checks})
