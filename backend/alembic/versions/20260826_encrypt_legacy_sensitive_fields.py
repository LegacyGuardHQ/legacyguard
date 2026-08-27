"""encrypt and remove legacy plaintext-sensitive fields

This is an intentionally irreversible contract migration. Deploy it during a
maintenance window with old application instances stopped: older revisions
still map the plaintext columns removed here. Back up the database first, keep
the deployment encryption key unchanged, and roll forward rather than running
an application rollback after this revision.

Revision ID: a6b7c8d9e0f1
Revises: f4a5b6c7d8e9
Create Date: 2026-08-26 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.services.encryption import EncryptionOperationError, encryption_service


revision = "a6b7c8d9e0f1"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def _validated_backfill_value(
    *,
    table_name: str,
    row_id: str,
    field_name: str,
    plaintext: str | None,
    encrypted: str | None,
) -> str | None:
    if encrypted is None:
        return encryption_service.encrypt(plaintext) if plaintext is not None else None

    try:
        decrypted = encryption_service.decrypt(encrypted)
    except EncryptionOperationError as exc:
        raise RuntimeError(
            f"Cannot migrate {table_name}.{field_name} for row {row_id}: existing ciphertext is invalid"
        ) from exc
    if plaintext is not None and decrypted != plaintext:
        raise RuntimeError(
            f"Cannot migrate {table_name}.{field_name} for row {row_id}: plaintext and ciphertext conflict"
        )
    return None


def _require_column_pair(table_name: str, columns: set[str], first: str, second: str) -> bool:
    present = {first, second}.intersection(columns)
    if present and present != {first, second}:
        raise RuntimeError(f"Cannot migrate {table_name}: legacy column pair is only partially present")
    return present == {first, second}


def _plan_beneficiary_backfill(bind: sa.Connection, columns: set[str]) -> list[tuple[str, dict[str, str]]]:
    if not _require_column_pair("beneficiaries", columns, "contact_information", "notes"):
        return []
    rows = bind.execute(
        sa.text(
            "SELECT id, contact_information, notes, contact_information_encrypted, notes_encrypted "
            "FROM beneficiaries"
        )
    ).mappings()
    planned_updates: list[tuple[str, dict[str, str]]] = []
    for row in rows:
        values: dict[str, str] = {}
        contact_information_encrypted = _validated_backfill_value(
            table_name="beneficiaries",
            row_id=row["id"],
            field_name="contact_information",
            plaintext=row["contact_information"],
            encrypted=row["contact_information_encrypted"],
        )
        notes_encrypted = _validated_backfill_value(
            table_name="beneficiaries",
            row_id=row["id"],
            field_name="notes",
            plaintext=row["notes"],
            encrypted=row["notes_encrypted"],
        )
        if contact_information_encrypted is not None:
            values["contact_information_encrypted"] = contact_information_encrypted
        if notes_encrypted is not None:
            values["notes_encrypted"] = notes_encrypted
        if values:
            planned_updates.append((row["id"], values))
    return planned_updates


def _plan_asset_detail_backfill(bind: sa.Connection, columns: set[str]) -> list[tuple[str, dict[str, str]]]:
    if not _require_column_pair(
        "asset_details", columns, "login_information_reference", "contact_information"
    ):
        return []
    login_ciphertext = (
        "login_information_reference_encrypted"
        if "login_information_reference_encrypted" in columns
        else "NULL AS login_information_reference_encrypted"
    )
    contact_ciphertext = (
        "contact_information_encrypted"
        if "contact_information_encrypted" in columns
        else "NULL AS contact_information_encrypted"
    )
    rows = bind.execute(
        sa.text(
            "SELECT id, login_information_reference, contact_information, "
            f"{login_ciphertext}, {contact_ciphertext} FROM asset_details"
        )
    ).mappings()
    planned_updates: list[tuple[str, dict[str, str]]] = []
    for row in rows:
        values: dict[str, str] = {}
        login_information_reference_encrypted = _validated_backfill_value(
            table_name="asset_details",
            row_id=row["id"],
            field_name="login_information_reference",
            plaintext=row["login_information_reference"],
            encrypted=row["login_information_reference_encrypted"],
        )
        contact_information_encrypted = _validated_backfill_value(
            table_name="asset_details",
            row_id=row["id"],
            field_name="contact_information",
            plaintext=row["contact_information"],
            encrypted=row["contact_information_encrypted"],
        )
        if login_information_reference_encrypted is not None:
            values["login_information_reference_encrypted"] = login_information_reference_encrypted
        if contact_information_encrypted is not None:
            values["contact_information_encrypted"] = contact_information_encrypted
        if values:
            planned_updates.append((row["id"], values))
    return planned_updates


def _apply_backfill(
    bind: sa.Connection,
    table_name: str,
    encrypted_columns: tuple[str, str],
    planned_updates: list[tuple[str, dict[str, str]]],
) -> None:
    table = sa.table(table_name, sa.column("id"), *(sa.column(name) for name in encrypted_columns))
    for row_id, values in planned_updates:
        bind.execute(sa.update(table).where(table.c.id == row_id).values(**values))


def _add_column_if_missing(table_name: str, columns: set[str], column_name: str) -> None:
    if column_name not in columns:
        op.add_column(table_name, sa.Column(column_name, sa.Text(), nullable=True))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    beneficiary_columns = {column["name"] for column in inspector.get_columns("beneficiaries")}
    asset_detail_columns = {column["name"] for column in inspector.get_columns("asset_details")}

    # Build and validate every row's update before changing schema or data. This
    # keeps a bad late row from leaving a partially applied SQLite migration.
    beneficiary_updates = _plan_beneficiary_backfill(bind, beneficiary_columns)
    asset_detail_updates = _plan_asset_detail_backfill(bind, asset_detail_columns)

    _add_column_if_missing(
        "asset_details",
        asset_detail_columns,
        "login_information_reference_encrypted",
    )
    _add_column_if_missing("asset_details", asset_detail_columns, "contact_information_encrypted")
    _apply_backfill(
        bind,
        "beneficiaries",
        ("contact_information_encrypted", "notes_encrypted"),
        beneficiary_updates,
    )
    _apply_backfill(
        bind,
        "asset_details",
        ("login_information_reference_encrypted", "contact_information_encrypted"),
        asset_detail_updates,
    )
    if {"contact_information", "notes"}.issubset(beneficiary_columns):
        with op.batch_alter_table("beneficiaries") as batch_op:
            batch_op.drop_column("contact_information")
            batch_op.drop_column("notes")
    if {"login_information_reference", "contact_information"}.issubset(asset_detail_columns):
        with op.batch_alter_table("asset_details") as batch_op:
            batch_op.drop_column("login_information_reference")
            batch_op.drop_column("contact_information")


def downgrade() -> None:
    raise RuntimeError("Downgrade is intentionally unsupported: this migration removes plaintext-sensitive columns.")
