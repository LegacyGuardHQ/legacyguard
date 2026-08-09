"""Add source_context to manual asset conversion provenance links.

Revision ID: c1d2e3f4a5b6
Revises: a2b3c4d5e6f7
Create Date: 2026-08-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4a5b6"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "discovery_finding_asset_links",
        sa.Column("source_context", sa.String(), nullable=False, server_default="manual_conversion"),
    )
    op.create_index(
        "ix_discovery_finding_asset_links_source_context",
        "discovery_finding_asset_links",
        ["source_context"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_discovery_finding_asset_links_source_context", table_name="discovery_finding_asset_links")
    op.drop_column("discovery_finding_asset_links", "source_context")
