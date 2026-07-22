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
    op.add_column("documents", sa.Column("beneficiary_id", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("description_encrypted", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("original_filename", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("mime_type", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("file_size", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("checksum_sha256", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("content_encryption_version", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("encryption_key_reference_encrypted", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("storage_reference_encrypted", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"))
    op.add_column("documents", sa.Column("verification_status", sa.String(), nullable=False, server_default="UNKNOWN"))
    op.add_column("documents", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("expiration_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("replaced_by_document_id", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
    op.create_index(op.f("ix_documents_beneficiary_id"), "documents", ["beneficiary_id"], unique=False)
    op.create_index(op.f("ix_documents_mime_type"), "documents", ["mime_type"], unique=False)
    op.create_index(op.f("ix_documents_checksum_sha256"), "documents", ["checksum_sha256"], unique=False)
    op.create_index(op.f("ix_documents_status"), "documents", ["status"], unique=False)
    op.create_index(op.f("ix_documents_verification_status"), "documents", ["verification_status"], unique=False)
    op.create_foreign_key("fk_documents_beneficiary_id_beneficiaries", "documents", "beneficiaries", ["beneficiary_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_documents_replaced_by_document_id_documents", "documents", "documents", ["replaced_by_document_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_documents_replaced_by_document_id_documents", "documents", type_="foreignkey")
    op.drop_constraint("fk_documents_beneficiary_id_beneficiaries", "documents", type_="foreignkey")
    op.drop_index(op.f("ix_documents_verification_status"), table_name="documents")
    op.drop_index(op.f("ix_documents_status"), table_name="documents")
    op.drop_index(op.f("ix_documents_checksum_sha256"), table_name="documents")
    op.drop_index(op.f("ix_documents_mime_type"), table_name="documents")
    op.drop_index(op.f("ix_documents_beneficiary_id"), table_name="documents")
    for column in (
        "version_number", "replaced_by_document_id", "archived_at", "expiration_date", "effective_date",
        "review_due_at", "verified_at", "verification_status", "status", "storage_reference_encrypted",
        "encryption_key_reference_encrypted", "content_encryption_version", "checksum_sha256", "file_size",
        "mime_type", "original_filename", "description_encrypted", "beneficiary_id",
    ):
        op.drop_column("documents", column)
