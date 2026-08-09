import os
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "application": "LegacyGuard"}


def test_live_endpoint() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_endpoint_reports_ok_when_dependencies_ready() -> None:
    with patch("app.api.health.check_database_ready", return_value=True), patch(
        "app.api.health.check_storage_ready", return_value=True
    ), patch("app.api.health.check_migration_ready", return_value=True):
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "storage": "ok", "migrations": "ok"},
    }


def test_ready_endpoint_reports_degraded_when_dependencies_fail() -> None:
    with patch("app.api.health.check_database_ready", return_value=False), patch(
        "app.api.health.check_storage_ready", return_value=False
    ), patch("app.api.health.check_migration_ready", return_value=False):
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "checks": {"database": "failed", "storage": "failed", "migrations": "failed"},
    }
