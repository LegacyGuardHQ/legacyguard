#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
import shutil
import sys
import tempfile
import time
import uuid
import gc
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def ensure_python_312() -> None:
    version = sys.version_info
    if not (version.major == 3 and version.minor == 12):
        raise SystemExit("This script must run with Python 3.12.x")


def clear_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def make_database_url(db_path: Path) -> str:
    return "sqlite:///" + db_path.resolve().as_posix()


def make_env(db_path: Path, docs_root: Path) -> dict[str, str]:
    return {
        "DATABASE_URL": make_database_url(db_path),
        "ENVIRONMENT": "production",
        "SECRET_KEY": "temporary-rc1-secret-key-123456",
        "JWT_SECRET": "temporary-rc1-jwt-secret-123456",
        "ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8"),
        "CORS_ALLOWED_ORIGINS": "https://example.com",
        "DEBUG": "false",
        "DOCUMENT_STORAGE_ROOT": str(docs_root),
        "PYTHONPATH": str(BACKEND_ROOT),
    }


def init_backend(env: dict[str, str]):
    clear_app_modules()
    os.environ.update(env)
    from app.services.alembic_readiness import upgrade_database_to_head

    upgrade_database_to_head(database_url=env["DATABASE_URL"])
    from app.main import app

    return app


def dispose_backend_engine() -> None:
    try:
        from app.database.connection import engine

        engine.dispose()
    except Exception:
        pass


def verify_health(app_instance) -> dict[str, object]:
    with TestClient(app_instance) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")
    return {
        "live_status": live.status_code,
        "live_body": live.json(),
        "ready_status": ready.status_code,
        "ready_body": ready.json(),
    }


def verify_smoke_equivalent(app_instance) -> dict[str, object]:
    with TestClient(app_instance) as client:
        login = client.post(
            "/auth/login",
            json={"email": "unknown@example.com", "password": "wrong"},
        )
    if login.status_code not in {200, 401, 403, 429}:
        raise SystemExit(f"auth endpoint unexpected status: {login.status_code}")
    return {"auth_login_status": login.status_code}


def seed_test_data(env: dict[str, str]) -> tuple[str, str, str]:
    clear_app_modules()
    os.environ.update(env)
    from app.services.document_storage import LocalDocumentStorage

    marker_id = "rc1-marker-001"
    marker_value = "recovery-verification"
    document_id = str(uuid.uuid4())
    db_path = Path(env["DATABASE_URL"].replace("sqlite:///", "", 1))
    with sqlite3.connect(str(db_path)) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS rc1_verification_markers (marker_id TEXT PRIMARY KEY, marker_value TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT OR REPLACE INTO rc1_verification_markers (marker_id, marker_value) VALUES (?, ?)",
            (marker_id, marker_value),
        )
        connection.commit()

    storage = LocalDocumentStorage(env["DOCUMENT_STORAGE_ROOT"])
    fernet = Fernet(env["ENCRYPTION_KEY"].encode("utf-8"))
    relative_path = storage.save_encrypted(
        document_id,
        fernet.encrypt(b"Temporary RC1 recovery verification document"),
    ).locator
    return marker_id, document_id, relative_path


def verify_database_record(marker_id: str) -> bool:
    from app.config import settings

    db_path = Path(settings.database_url.replace("sqlite:///", "", 1))
    with sqlite3.connect(str(db_path)) as connection:
        cursor = connection.execute(
            "SELECT marker_id FROM rc1_verification_markers WHERE marker_id = ?",
            (marker_id,),
        )
        return cursor.fetchone() is not None


def verify_sqlite_opens_and_has_table(db_path: Path) -> bool:
    if not db_path.exists() or db_path.stat().st_size <= 0:
        return False
    with sqlite3.connect(str(db_path)) as connection:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        row = cursor.fetchone()
        return row is not None


def verify_document_exists(storage_locator: str, document_root: str) -> bool:
    from app.services.document_storage import LocalDocumentStorage

    storage = LocalDocumentStorage(document_root)
    return storage.exists(storage_locator)


def assert_health_ok(label: str, health: dict[str, Any]) -> None:
    print(f"{label}_HEALTH", json.dumps(health, sort_keys=True))
    if health["live_status"] != 200:
        raise SystemExit(f"{label.lower()} live health check failed")
    if health["ready_status"] != 200:
        raise SystemExit(f"{label.lower()} ready health check failed")


def cleanup_temp_root(temp_root: Path) -> bool:
    for _ in range(8):
        if not temp_root.exists():
            return True
        gc.collect()
        shutil.rmtree(temp_root, ignore_errors=True)
        if not temp_root.exists():
            return True
        time.sleep(0.25)
    return not temp_root.exists()


def main() -> int:
    ensure_python_312()

    temp_root = Path(tempfile.mkdtemp(prefix="legacyguard_rc1_"))
    cleanup_ok = False
    try:
        active_root = temp_root / "active"
        backup_root = temp_root / "backup"
        restore_root = temp_root / "restore"
        candidate_root = temp_root / "candidate"
        rollback_root = temp_root / "rollback"
        for directory in (active_root, backup_root, restore_root, candidate_root, rollback_root):
            directory.mkdir(parents=True, exist_ok=True)

        active_db = active_root / "legacyguard.db"
        active_docs = active_root / "documents"
        active_docs.mkdir(parents=True, exist_ok=True)
        active_env = make_env(active_db, active_docs)

        app = init_backend(active_env)
        marker_id, document_id, document_relative_path = seed_test_data(active_env)

        active_health = verify_health(app)
        assert_health_ok("ACTIVE", active_health)
        active_smoke = verify_smoke_equivalent(app)
        print("ACTIVE_SMOKE", json.dumps(active_smoke, sort_keys=True))
        dispose_backend_engine()
        del app
        gc.collect()

        backup_db = backup_root / "legacyguard.db"
        backup_docs = backup_root / "documents"
        shutil.copy2(active_db, backup_db)
        shutil.copytree(active_docs, backup_docs, dirs_exist_ok=True)
        backup_artifact = backup_docs / document_relative_path
        if not backup_db.exists() or backup_db.stat().st_size <= 0:
            raise SystemExit("backup database missing or empty")
        if not backup_docs.exists() or not any(backup_docs.rglob("*")):
            raise SystemExit("backup storage missing or empty")
        if not os.access(backup_db, os.R_OK):
            raise SystemExit("backup database is not readable")
        if not backup_artifact.exists() or not os.access(backup_artifact, os.R_OK):
            raise SystemExit("backup artifact missing or not readable")
        if not verify_sqlite_opens_and_has_table(backup_db):
            raise SystemExit("backup creation failed")
        print("BACKUP_EXECUTED_AND_VERIFIED")

        restore_db = restore_root / "legacyguard.db"
        restore_docs = restore_root / "documents"
        shutil.copy2(backup_db, restore_db)
        shutil.copytree(backup_docs, restore_docs, dirs_exist_ok=True)
        restore_env = make_env(restore_db, restore_docs)
        restore_env["ENCRYPTION_KEY"] = active_env["ENCRYPTION_KEY"]
        restore_env["SECRET_KEY"] = active_env["SECRET_KEY"]
        restore_env["JWT_SECRET"] = active_env["JWT_SECRET"]

        restore_app = init_backend(restore_env)
        if not verify_sqlite_opens_and_has_table(restore_db):
            raise SystemExit("restored database did not open as expected")
        if not verify_database_record(marker_id):
            raise SystemExit("restored database record missing")
        if not verify_document_exists(document_relative_path, str(restore_docs)):
            raise SystemExit("restored document missing")
        restore_health = verify_health(restore_app)
        assert_health_ok("RESTORE", restore_health)
        restore_smoke = verify_smoke_equivalent(restore_app)
        print("RESTORE_SMOKE", json.dumps(restore_smoke, sort_keys=True))
        print("RESTORE_EXECUTED_AND_VERIFIED")
        dispose_backend_engine()
        del restore_app
        gc.collect()

        candidate_db = candidate_root / "legacyguard.db"
        candidate_docs = candidate_root / "documents"
        shutil.copy2(restore_db, candidate_db)
        shutil.copytree(restore_docs, candidate_docs, dirs_exist_ok=True)
        candidate_env = make_env(candidate_db, candidate_docs)
        candidate_env["ENCRYPTION_KEY"] = active_env["ENCRYPTION_KEY"]
        candidate_env["SECRET_KEY"] = active_env["SECRET_KEY"]
        candidate_env["JWT_SECRET"] = active_env["JWT_SECRET"]

        candidate_app = init_backend(candidate_env)
        candidate_health = verify_health(candidate_app)
        assert_health_ok("CANDIDATE", candidate_health)
        candidate_smoke = verify_smoke_equivalent(candidate_app)
        print("CANDIDATE_SMOKE", json.dumps(candidate_smoke, sort_keys=True))
        dispose_backend_engine()
        del candidate_app
        gc.collect()

        # Simulate a deployment regression in temporary artifacts only.
        if candidate_db.exists():
            candidate_db.unlink()
        shutil.rmtree(candidate_docs, ignore_errors=True)

        rollback_db = rollback_root / "legacyguard.db"
        rollback_docs = rollback_root / "documents"
        shutil.copy2(backup_db, rollback_db)
        shutil.copytree(backup_docs, rollback_docs, dirs_exist_ok=True)
        rollback_env = make_env(rollback_db, rollback_docs)
        rollback_env["ENCRYPTION_KEY"] = active_env["ENCRYPTION_KEY"]
        rollback_env["SECRET_KEY"] = active_env["SECRET_KEY"]
        rollback_env["JWT_SECRET"] = active_env["JWT_SECRET"]

        rollback_app = init_backend(rollback_env)
        if not verify_sqlite_opens_and_has_table(rollback_db):
            raise SystemExit("rollback database did not open as expected")
        if not verify_database_record(marker_id):
            raise SystemExit("rollback database record missing")
        if not verify_document_exists(document_relative_path, str(rollback_docs)):
            raise SystemExit("rollback document missing")
        rollback_health = verify_health(rollback_app)
        assert_health_ok("ROLLBACK", rollback_health)
        rollback_smoke = verify_smoke_equivalent(rollback_app)
        print("ROLLBACK_SMOKE", json.dumps(rollback_smoke, sort_keys=True))
        print("ROLLBACK_EXECUTED_AND_VERIFIED")
        dispose_backend_engine()
        del rollback_app
        gc.collect()
    finally:
        dispose_backend_engine()
        clear_app_modules()
        cleanup_ok = cleanup_temp_root(temp_root)

    if not cleanup_ok:
        raise SystemExit("temporary cleanup failed")

    print("CLEANUP_SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
