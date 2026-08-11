from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.config import settings


def _alembic_config(database_url: str | None = None) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    if database_url is not None:
        config.set_main_option("sqlalchemy.url", database_url)
    return config


def _get_current_revision(database_url: str | None = None) -> str | None:
    config = _alembic_config(database_url)
    engine = create_engine(database_url or settings.database_url)
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            return row[0] if row is not None else None
    except Exception:
        return None
    finally:
        engine.dispose()


def _get_head_revision(database_url: str | None = None) -> str | None:
    config = _alembic_config(database_url)
    try:
        from alembic.script import ScriptDirectory

        script_dir = ScriptDirectory.from_config(config)
        return script_dir.get_current_head()
    except Exception:
        return None


def check_migration_readiness(database_url: str | None = None) -> bool:
    current_revision = _get_current_revision(database_url)
    expected_head = _get_head_revision(database_url)
    if not current_revision or not expected_head:
        return False
    return current_revision == expected_head


def upgrade_database_to_head(database_url: str | None = None) -> None:
    config = _alembic_config(database_url)
    command.upgrade(config, "head")
