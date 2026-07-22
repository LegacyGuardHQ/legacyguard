"""Asset model preparation

Revision ID: 8d3c2f1a9b70
Revises: 3f4afebac2b9
Create Date: 2026-07-09 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "8d3c2f1a9b70"
down_revision = "3f4afebac2b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("assets", sa.Column("verification_status", sa.String(), nullable=False, server_default="UNKNOWN"))
    op.add_column("assets", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("assets", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("asset_details", sa.Column("claim_instructions_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("asset_details", "claim_instructions_encrypted")
    op.drop_column("assets", "archived_at")
    op.drop_column("assets", "verified_at")
    op.drop_column("assets", "verification_status")
    op.drop_column("assets", "is_verified")