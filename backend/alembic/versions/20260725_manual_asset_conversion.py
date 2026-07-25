"""Add explicit discovery finding to asset conversion links.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-25 09:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "a2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discovery_finding_asset_links",
        sa.Column("finding_id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["finding_id"], ["evidence_findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("finding_id"),
        sa.UniqueConstraint("asset_id"),
    )
    op.create_index(
        "ix_discovery_finding_asset_links_asset_id",
        "discovery_finding_asset_links",
        ["asset_id"],
        unique=True,
    )
    op.create_index(
        "ix_discovery_finding_asset_links_user_id",
        "discovery_finding_asset_links",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_discovery_finding_asset_links_user_id", table_name="discovery_finding_asset_links")
    op.drop_index("ix_discovery_finding_asset_links_asset_id", table_name="discovery_finding_asset_links")
    op.drop_table("discovery_finding_asset_links")
