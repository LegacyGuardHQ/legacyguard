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
    # SQLite supports ADD COLUMN directly for these nullable/defaulted columns.
    # Adding them individually avoids Alembic batch-recreate ordering cycles.
    for column in (
        sa.Column("contact_information_encrypted", sa.Text(), nullable=True),
        sa.Column("notes_encrypted", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="Active"),
        sa.Column("verification_status", sa.String(), nullable=False, server_default="UNKNOWN"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deceased", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deceased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    ):
        op.add_column("beneficiaries", column)

    op.add_column(
        "asset_beneficiaries",
        sa.Column("beneficiary_role", sa.String(), nullable=False, server_default="PRIMARY"),
    )
    op.add_column(
        "asset_beneficiaries",
        sa.Column("priority_order", sa.String(), nullable=True),
    )

    # SQLite requires table recreation for new table-level constraints.
    with op.batch_alter_table("asset_beneficiaries") as batch_op:
        batch_op.create_unique_constraint(
            "uq_asset_beneficiary_asset_beneficiary",
            ["asset_id", "beneficiary_id"],
        )
        batch_op.create_check_constraint(
            "ck_asset_beneficiary_percentage_range",
            "percentage IS NULL OR (percentage >= 0 AND percentage <= 100)",
        )


def downgrade() -> None:
    with op.batch_alter_table("asset_beneficiaries") as batch_op:
        batch_op.drop_constraint("ck_asset_beneficiary_percentage_range", type_="check")
        batch_op.drop_constraint("uq_asset_beneficiary_asset_beneficiary", type_="unique")

    op.drop_column("asset_beneficiaries", "priority_order")
    op.drop_column("asset_beneficiaries", "beneficiary_role")

    for column_name in (
        "archived_at",
        "deceased_at",
        "is_deceased",
        "review_due_at",
        "verified_at",
        "verification_status",
        "status",
        "notes_encrypted",
        "contact_information_encrypted",
    ):
        op.drop_column("beneficiaries", column_name)
