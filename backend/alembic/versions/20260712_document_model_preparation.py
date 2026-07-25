"""Document model preparation

Revision ID: d2f4b8c9a701
Revises: c7a2d91f5e63
Create Date: 2026-07-12 04:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d2f4b8c9a701"
down_revision = "c7a2d91f5e63"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("documents", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("beneficiary_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("description_encrypted", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("original_filename", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("mime_type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("file_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("checksum_sha256", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("content_encryption_version", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("encryption_key_reference_encrypted", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("storage_reference_encrypted", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"))
        batch_op.add_column(sa.Column("verification_status", sa.String(), nullable=False, server_default="UNKNOWN"))
        batch_op.add_column(sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("expiration_date", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("replaced_by_document_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_index(op.f("ix_documents_beneficiary_id"), ["beneficiary_id"], unique=False)
        batch_op.create_index(op.f("ix_documents_mime_type"), ["mime_type"], unique=False)
        batch_op.create_index(op.f("ix_documents_checksum_sha256"), ["checksum_sha256"], unique=False)
        batch_op.create_index(op.f("ix_documents_status"), ["status"], unique=False)
        batch_op.create_index(op.f("ix_documents_verification_status"), ["verification_status"], unique=False)
        batch_op.create_foreign_key(
            "fk_documents_beneficiary_id_beneficiaries",
            "beneficiaries",
            ["beneficiary_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_documents_replaced_by_document_id_documents",
            "documents",
            ["replaced_by_document_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("documents", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_documents_replaced_by_document_id_documents", type_="foreignkey")
        batch_op.drop_constraint("fk_documents_beneficiary_id_beneficiaries", type_="foreignkey")
        batch_op.drop_index(op.f("ix_documents_verification_status"))
        batch_op.drop_index(op.f("ix_documents_status"))
        batch_op.drop_index(op.f("ix_documents_checksum_sha256"))
        batch_op.drop_index(op.f("ix_documents_mime_type"))
        batch_op.drop_index(op.f("ix_documents_beneficiary_id"))
        for column in (
            "version_number",
            "replaced_by_document_id",
            "archived_at",
            "expiration_date",
            "effective_date",
            "review_due_at",
            "verified_at",
            "verification_status",
            "status",
            "storage_reference_encrypted",
            "encryption_key_reference_encrypted",
            "content_encryption_version",
            "checksum_sha256",
            "file_size",
            "mime_type",
            "original_filename",
            "description_encrypted",
            "beneficiary_id",
        ):
            batch_op.drop_column(column)
