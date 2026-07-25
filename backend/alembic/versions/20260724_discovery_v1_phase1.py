"""Discovery Intelligence v1.0 phase 1

Revision ID: e4c7a9b2d611
Revises: fb94d1fd5ad1
Create Date: 2026-07-24 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "e4c7a9b2d611"
down_revision = "fb94d1fd5ad1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("metadata", sa.JSON(), nullable=True))
    op.create_table(
        "discovery_scan_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("scan_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("warning_code", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["discovery_scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_discovery_scan_documents_id"),
        "discovery_scan_documents",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_scan_documents_scan_id"),
        "discovery_scan_documents",
        ["scan_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_scan_documents_document_id"),
        "discovery_scan_documents",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_scan_documents_status"),
        "discovery_scan_documents",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_discovery_scan_documents_status"), table_name="discovery_scan_documents")
    op.drop_index(op.f("ix_discovery_scan_documents_document_id"), table_name="discovery_scan_documents")
    op.drop_index(op.f("ix_discovery_scan_documents_scan_id"), table_name="discovery_scan_documents")
    op.drop_index(op.f("ix_discovery_scan_documents_id"), table_name="discovery_scan_documents")
    op.drop_table("discovery_scan_documents")
    op.drop_column("audit_logs", "metadata")
