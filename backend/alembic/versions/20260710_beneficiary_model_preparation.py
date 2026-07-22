"""Beneficiary model preparation

Revision ID: b91f6d2c4a18
Revises: 8d3c2f1a9b70
Create Date: 2026-07-10 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b91f6d2c4a18"
down_revision = "8d3c2f1a9b70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("beneficiaries", sa.Column("contact_information_encrypted", sa.Text(), nullable=True))
    op.add_column("beneficiaries", sa.Column("notes_encrypted", sa.Text(), nullable=True))
    op.add_column("beneficiaries", sa.Column("status", sa.String(), nullable=False, server_default="Active"))
    op.add_column("beneficiaries", sa.Column("verification_status", sa.String(), nullable=False, server_default="UNKNOWN"))
    op.add_column("beneficiaries", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("beneficiaries", sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("beneficiaries", sa.Column("is_deceased", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("beneficiaries", sa.Column("deceased_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("beneficiaries", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("asset_beneficiaries", sa.Column("beneficiary_role", sa.String(), nullable=False, server_default="PRIMARY"))
    op.add_column("asset_beneficiaries", sa.Column("priority_order", sa.String(), nullable=True))
    op.create_unique_constraint("uq_asset_beneficiary_asset_beneficiary", "asset_beneficiaries", ["asset_id", "beneficiary_id"])
    op.create_check_constraint(
        "ck_asset_beneficiary_percentage_range",
        "asset_beneficiaries",
        "percentage IS NULL OR (percentage >= 0 AND percentage <= 100)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_asset_beneficiary_percentage_range", "asset_beneficiaries", type_="check")
    op.drop_constraint("uq_asset_beneficiary_asset_beneficiary", "asset_beneficiaries", type_="unique")
    op.drop_column("asset_beneficiaries", "priority_order")
    op.drop_column("asset_beneficiaries", "beneficiary_role")
    op.drop_column("beneficiaries", "archived_at")
    op.drop_column("beneficiaries", "deceased_at")
    op.drop_column("beneficiaries", "is_deceased")
    op.drop_column("beneficiaries", "review_due_at")
    op.drop_column("beneficiaries", "verified_at")
    op.drop_column("beneficiaries", "verification_status")
    op.drop_column("beneficiaries", "status")
    op.drop_column("beneficiaries", "notes_encrypted")
    op.drop_column("beneficiaries", "contact_information_encrypted")