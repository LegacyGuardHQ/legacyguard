"""Add provider-neutral document storage state and integrity metadata.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-08-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("storage_backend", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("storage_provider_version", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("storage_state", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("storage_state_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("storage_error_code", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("upload_attempt_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("ciphertext_sha256", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("ciphertext_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("master_key_id", sa.String(), nullable=True))

    op.execute(sa.text("UPDATE documents SET storage_backend = 'LOCAL'"))
    op.execute(
        sa.text(
            "UPDATE documents SET storage_state = CASE "
            "WHEN storage_reference_encrypted IS NOT NULL "
            "AND encryption_key_reference_encrypted IS NOT NULL THEN 'STORED' "
            "ELSE 'PENDING' END"
        )
    )
    op.execute(sa.text("UPDATE documents SET storage_state_updated_at = updated_at"))
    op.execute(
        sa.text(
            "UPDATE documents SET master_key_id = 'legacy-current-v1' "
            "WHERE storage_state = 'STORED'"
        )
    )

    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column("storage_backend", existing_type=sa.String(), nullable=False, server_default="LOCAL")
        batch_op.alter_column("storage_state", existing_type=sa.String(), nullable=False, server_default="PENDING")
        batch_op.create_check_constraint(
            "ck_documents_storage_state",
            "storage_state IN ('PENDING', 'STORED', 'FAILED')",
        )
        batch_op.create_index("ix_documents_storage_backend", ["storage_backend"], unique=False)
        batch_op.create_index("ix_documents_storage_state", ["storage_state"], unique=False)
        batch_op.create_index("ix_documents_upload_attempt_id", ["upload_attempt_id"], unique=True)
        batch_op.create_index("ix_documents_master_key_id", ["master_key_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_index("ix_documents_master_key_id")
        batch_op.drop_index("ix_documents_upload_attempt_id")
        batch_op.drop_index("ix_documents_storage_state")
        batch_op.drop_index("ix_documents_storage_backend")
        batch_op.drop_constraint("ck_documents_storage_state", type_="check")
        for column in (
            "master_key_id",
            "ciphertext_size",
            "ciphertext_sha256",
            "upload_attempt_id",
            "storage_error_code",
            "storage_state_updated_at",
            "storage_state",
            "storage_provider_version",
            "storage_backend",
        ):
            batch_op.drop_column(column)
