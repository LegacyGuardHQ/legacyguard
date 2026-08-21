import os
import subprocess
import sys
from pathlib import Path

from app.services.alembic_readiness import check_migration_readiness


def test_alembic_cli_uses_database_url_environment_variable(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "deployment-target.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": database_url,
            "ENVIRONMENT": "testing",
            "PYTHONPATH": str(backend_root),
        }
    )

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert database_path.exists()

    assert check_migration_readiness(database_url=database_url) is True
