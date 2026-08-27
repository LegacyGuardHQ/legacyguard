import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


def _run_alembic(backend_root: Path, database_url: str, *arguments: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": database_url,
            "ENVIRONMENT": "testing",
            "PYTHONPATH": str(backend_root),
        }
    )
    environment.pop("DEBUG", None)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_rc_document_rows_backfill_and_downgrade_without_reference_loss(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "rc-upgrade.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)

    _run_alembic(backend_root, database_url, "upgrade", "e3f4a5b6c7d8")
    with engine.begin() as connection:
        for document_id, storage_reference, key_reference in (
            ("stored-document", "encrypted-local-reference", "encrypted-dek"),
            ("metadata-only-document", None, None),
        ):
            connection.execute(
                text(
                    "INSERT INTO documents "
                    "(id, user_id, document_type, document_name, encrypted, status, verification_status, "
                    "version_number, created_at, updated_at, storage_reference_encrypted, encryption_key_reference_encrypted) "
                    "VALUES (:id, 'legacy-user', 'WILL', 'Legacy document', 1, 'ACTIVE', 'UNKNOWN', "
                    "1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :storage_reference, :key_reference)"
                ),
                {
                    "id": document_id,
                    "storage_reference": storage_reference,
                    "key_reference": key_reference,
                },
            )

    _run_alembic(backend_root, database_url, "upgrade", "f4a5b6c7d8e9")
    with engine.connect() as connection:
        rows = {
            row.id: row
            for row in connection.execute(
                text(
                    "SELECT id, storage_state, storage_backend, master_key_id, "
                    "storage_reference_encrypted FROM documents"
                )
            )
        }
        assert rows["stored-document"].storage_state == "STORED"
        assert rows["stored-document"].storage_backend == "LOCAL"
        assert rows["stored-document"].master_key_id == "legacy-current-v1"
        assert rows["stored-document"].storage_reference_encrypted == "encrypted-local-reference"
        assert rows["metadata-only-document"].storage_state == "PENDING"
        assert rows["metadata-only-document"].master_key_id is None

    _run_alembic(backend_root, database_url, "downgrade", "e3f4a5b6c7d8")
    assert "storage_state" not in {column["name"] for column in inspect(engine).get_columns("documents")}
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT storage_reference_encrypted FROM documents WHERE id = 'stored-document'")
        ).scalar_one() == "encrypted-local-reference"
