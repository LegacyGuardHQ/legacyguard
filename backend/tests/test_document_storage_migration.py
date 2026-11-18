import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


def _run_alembic(
    backend_root: Path,
    database_url: str,
    *arguments: str,
    expected_returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
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
    assert result.returncode == expected_returncode, result.stderr
    return result


def test_rc_document_rows_backfill_and_downgrade_refusal_preserves_state(tmp_path: Path) -> None:
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

    _run_alembic(backend_root, database_url, "upgrade", "head")
    with engine.connect() as connection:
        rows = {
            row.id: row
            for row in connection.execute(
                text(
                    "SELECT id, storage_state, storage_backend, master_key_id, "
                    "storage_reference_encrypted, malware_scan_status FROM documents"
                )
            )
        }
        assert rows["stored-document"].storage_state == "STORED"
        assert rows["stored-document"].storage_backend == "LOCAL"
        assert rows["stored-document"].master_key_id == "legacy-current-v1"
        assert rows["stored-document"].storage_reference_encrypted == "encrypted-local-reference"
        assert rows["stored-document"].malware_scan_status == "NOT_SCANNED"
        assert rows["metadata-only-document"].storage_state == "PENDING"
        assert rows["metadata-only-document"].master_key_id is None
        assert rows["metadata-only-document"].malware_scan_status == "NOT_SCANNED"

    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE documents SET malware_scan_status = CASE id "
                "WHEN 'stored-document' THEN 'CLEAN' "
                "WHEN 'metadata-only-document' THEN 'DETECTED' END"
            )
        )

    downgrade_result = _run_alembic(
        backend_root,
        database_url,
        "downgrade",
        "a6b7c8d9e0f1",
        expected_returncode=1,
    )
    assert "roll-forward-only" in downgrade_result.stderr
    assert "malware_scan_status" in {column["name"] for column in inspect(engine).get_columns("documents")}
    with engine.connect() as connection:
        rows = {
            row.id: row
            for row in connection.execute(
                text(
                    "SELECT id, storage_reference_encrypted, malware_scan_status "
                    "FROM documents ORDER BY id"
                )
            )
        }
        assert rows["stored-document"].storage_reference_encrypted == "encrypted-local-reference"
        assert rows["stored-document"].malware_scan_status == "CLEAN"
        assert rows["metadata-only-document"].malware_scan_status == "DETECTED"

    _run_alembic(backend_root, database_url, "upgrade", "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "b7c8d9e0f1a2"


def test_document_malware_migration_has_one_head(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{(tmp_path / 'head-check.db').as_posix()}"

    heads_result = _run_alembic(backend_root, database_url, "heads")

    assert heads_result.stdout.count("(head)") == 1
    assert "b7c8d9e0f1a2" in heads_result.stdout
