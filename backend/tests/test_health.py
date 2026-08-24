import os
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.services.alembic_readiness import (
    check_migration_readiness,
    upgrade_database_to_head,
)

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.main import app
from app.api import health as health_api
from app.services.document_storage import StorageReadiness

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


def test_storage_readiness_uses_non_destructive_backend_contract() -> None:
    with patch.object(
        health_api.document_storage,
        "check_readiness",
        return_value=StorageReadiness(configuration_valid=True, reachable=True, write_ready=None),
    ) as readiness:
        assert health_api.check_storage_ready() is True

    readiness.assert_called_once_with()


def test_storage_readiness_fails_closed_on_known_non_writable_backend() -> None:
    with patch.object(
        health_api.document_storage,
        "check_readiness",
        return_value=StorageReadiness(configuration_valid=True, reachable=True, write_ready=False),
    ):
        assert health_api.check_storage_ready() is False


def test_migration_readiness_reports_healthy_after_upgrade(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'legacyguard-upgraded.db'}"
    upgrade_database_to_head(database_url=database_url)

    assert check_migration_readiness(database_url=database_url) is True


def test_migration_readiness_reports_unhealthy_for_unmigrated_database(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'legacyguard-stale.db'}"

    assert check_migration_readiness(database_url=database_url) is False


def test_migration_readiness_reports_unhealthy_when_revision_lookup_fails() -> None:
    assert check_migration_readiness(database_url="sqlite:///:memory:") is False
