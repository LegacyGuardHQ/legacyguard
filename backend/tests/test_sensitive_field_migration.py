import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text


TEST_ENCRYPTION_KEY = "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE="
os.environ.setdefault("ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)

from app.services.encryption import EncryptionService


def _invoke_alembic(backend_root: Path, database_url: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": database_url,
            "ENCRYPTION_KEY": TEST_ENCRYPTION_KEY,
            "ENVIRONMENT": "testing",
            "PYTHONPATH": str(backend_root),
        }
    )
    environment.pop("DEBUG", None)
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_alembic(backend_root: Path, database_url: str, *arguments: str) -> None:
    result = _invoke_alembic(backend_root, database_url, *arguments)
    assert result.returncode == 0, result.stderr


def _seed_legacy_schema(engine, *, conflicting_ciphertext: str | None = None) -> None:
    cipher = EncryptionService(TEST_ENCRYPTION_KEY)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users "
                "(id, email, password_hash, created_at, updated_at, is_active, role) "
                "VALUES ('legacy-user', 'legacy@example.com', 'hash', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, 'USER')"
            )
        )
        for asset_id, asset_name in (("asset-plain", "Plain asset"), ("asset-empty", "Empty asset")):
            connection.execute(
                text(
                    "INSERT INTO assets "
                    "(id, user_id, asset_category, asset_name, status, created_at, updated_at) "
                    "VALUES (:id, 'legacy-user', 'BANK', :name, 'Active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"id": asset_id, "name": asset_name},
            )
        connection.execute(
            text(
                "INSERT INTO asset_details "
                "(id, asset_id, login_information_reference, contact_information, created_at, updated_at) "
                "VALUES "
                "('detail-plain', 'asset-plain', 'legacy-login-reference', 'legacy-contact', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), "
                "('detail-empty', 'asset-empty', '', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        beneficiary_rows = (
            {
                "id": "beneficiary-plain",
                "contact": "legacy-beneficiary-contact",
                "notes": "legacy-beneficiary-notes",
                "contact_encrypted": None,
                "notes_encrypted": None,
            },
            {
                "id": "beneficiary-empty",
                "contact": "",
                "notes": "",
                "contact_encrypted": None,
                "notes_encrypted": None,
            },
            {
                "id": "beneficiary-null",
                "contact": None,
                "notes": None,
                "contact_encrypted": None,
                "notes_encrypted": None,
            },
            {
                "id": "beneficiary-existing",
                "contact": "already-protected",
                "notes": None,
                "contact_encrypted": conflicting_ciphertext or cipher.encrypt("already-protected"),
                "notes_encrypted": None,
            },
        )
        for row in beneficiary_rows:
            connection.execute(
                text(
                    "INSERT INTO beneficiaries "
                    "(id, user_id, name, contact_information, notes, contact_information_encrypted, notes_encrypted, "
                    "created_at, updated_at) "
                    "VALUES (:id, 'legacy-user', :id, :contact, :notes, :contact_encrypted, :notes_encrypted, "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                row,
            )


def test_legacy_sensitive_values_are_encrypted_verified_and_plaintext_columns_removed(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "legacy-sensitive.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    cipher = EncryptionService(TEST_ENCRYPTION_KEY)

    _run_alembic(backend_root, database_url, "upgrade", "f4a5b6c7d8e9")
    _seed_legacy_schema(engine)
    _run_alembic(backend_root, database_url, "upgrade", "head")
    # A second upgrade is a no-op and proves normal deployment retry behavior.
    _run_alembic(backend_root, database_url, "upgrade", "head")

    inspector = inspect(engine)
    beneficiary_columns = {column["name"] for column in inspector.get_columns("beneficiaries")}
    asset_detail_columns = {column["name"] for column in inspector.get_columns("asset_details")}
    assert {"contact_information", "notes"}.isdisjoint(beneficiary_columns)
    assert {"login_information_reference", "contact_information"}.isdisjoint(asset_detail_columns)
    assert {"contact_information_encrypted", "notes_encrypted"}.issubset(beneficiary_columns)
    assert {"login_information_reference_encrypted", "contact_information_encrypted"}.issubset(asset_detail_columns)

    with engine.connect() as connection:
        beneficiary_rows = {
            row.id: row
            for row in connection.execute(
                text("SELECT id, contact_information_encrypted, notes_encrypted FROM beneficiaries")
            )
        }
        asset_rows = {
            row.id: row
            for row in connection.execute(
                text(
                    "SELECT id, login_information_reference_encrypted, contact_information_encrypted "
                    "FROM asset_details"
                )
            )
        }
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "a6b7c8d9e0f1"

    assert cipher.decrypt(beneficiary_rows["beneficiary-plain"].contact_information_encrypted) == "legacy-beneficiary-contact"
    assert cipher.decrypt(beneficiary_rows["beneficiary-plain"].notes_encrypted) == "legacy-beneficiary-notes"
    assert cipher.decrypt(beneficiary_rows["beneficiary-empty"].contact_information_encrypted) == ""
    assert cipher.decrypt(beneficiary_rows["beneficiary-empty"].notes_encrypted) == ""
    assert beneficiary_rows["beneficiary-null"].contact_information_encrypted is None
    assert beneficiary_rows["beneficiary-null"].notes_encrypted is None
    assert cipher.decrypt(beneficiary_rows["beneficiary-existing"].contact_information_encrypted) == "already-protected"
    assert cipher.decrypt(asset_rows["detail-plain"].login_information_reference_encrypted) == "legacy-login-reference"
    assert cipher.decrypt(asset_rows["detail-plain"].contact_information_encrypted) == "legacy-contact"
    assert cipher.decrypt(asset_rows["detail-empty"].login_information_reference_encrypted) == ""
    assert asset_rows["detail-empty"].contact_information_encrypted is None

    asset_indexes = {index["name"]: index for index in inspector.get_indexes("asset_details")}
    beneficiary_indexes = {index["name"] for index in inspector.get_indexes("beneficiaries")}
    assert asset_indexes["ix_asset_details_asset_id"]["unique"] == 1
    assert {"ix_beneficiaries_id", "ix_beneficiaries_name", "ix_beneficiaries_user_id"}.issubset(beneficiary_indexes)


@pytest.mark.parametrize(
    "conflicting_ciphertext",
    [
        "not-a-valid-fernet-token",
        EncryptionService(TEST_ENCRYPTION_KEY).encrypt("different-value"),
    ],
)
def test_invalid_or_conflicting_ciphertext_aborts_before_plaintext_is_dropped(
    tmp_path: Path,
    conflicting_ciphertext: str,
) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "legacy-conflict.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    _run_alembic(backend_root, database_url, "upgrade", "f4a5b6c7d8e9")
    _seed_legacy_schema(engine, conflicting_ciphertext=conflicting_ciphertext)
    result = _invoke_alembic(backend_root, database_url, "upgrade", "head")

    assert result.returncode != 0
    beneficiary_columns = {column["name"] for column in inspect(engine).get_columns("beneficiaries")}
    asset_detail_columns = {column["name"] for column in inspect(engine).get_columns("asset_details")}
    assert {"contact_information", "notes"}.issubset(beneficiary_columns)
    assert {
        "login_information_reference_encrypted",
        "contact_information_encrypted",
    }.isdisjoint(asset_detail_columns)
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT contact_information, contact_information_encrypted "
                "FROM beneficiaries WHERE id = 'beneficiary-plain'"
            )
        ).one()
    assert row.contact_information == "legacy-beneficiary-contact"
    assert row.contact_information_encrypted is None


def test_upgrade_recovers_from_partially_added_asset_ciphertext_columns(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "legacy-partial-schema.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    cipher = EncryptionService(TEST_ENCRYPTION_KEY)

    _run_alembic(backend_root, database_url, "upgrade", "f4a5b6c7d8e9")
    _seed_legacy_schema(engine)
    preserved_ciphertext = cipher.encrypt("legacy-login-reference")
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE asset_details ADD COLUMN login_information_reference_encrypted TEXT"))
        connection.execute(
            text(
                "UPDATE asset_details SET login_information_reference_encrypted = :ciphertext "
                "WHERE id = 'detail-plain'"
            ),
            {"ciphertext": preserved_ciphertext},
        )

    _run_alembic(backend_root, database_url, "upgrade", "head")

    columns = {column["name"] for column in inspect(engine).get_columns("asset_details")}
    assert {"login_information_reference", "contact_information"}.isdisjoint(columns)
    assert {
        "login_information_reference_encrypted",
        "contact_information_encrypted",
    }.issubset(columns)
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT login_information_reference_encrypted, contact_information_encrypted "
                "FROM asset_details WHERE id = 'detail-plain'"
            )
        ).one()
    assert row.login_information_reference_encrypted == preserved_ciphertext
    assert cipher.decrypt(row.contact_information_encrypted) == "legacy-contact"
