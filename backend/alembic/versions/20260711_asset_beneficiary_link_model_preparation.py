"""Asset beneficiary link model preparation

Revision ID: c7a2d91f5e63
Revises: b91f6d2c4a18
Create Date: 2026-07-11 13:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c7a2d91f5e63"
down_revision = "b91f6d2c4a18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("asset_beneficiaries", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("priority_order_int", sa.Integer(), nullable=True))

    op.execute(
        "UPDATE asset_beneficiaries "
        "SET priority_order_int = CAST(priority_order AS INTEGER) "
        "WHERE priority_order IS NOT NULL AND priority_order GLOB '[0-9]*'"
    )

    with op.batch_alter_table("asset_beneficiaries", recreate="always") as batch_op:
        batch_op.drop_column("priority_order")
        batch_op.alter_column("priority_order_int", new_column_name="priority_order")
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deactivation_reason_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("asset_beneficiaries", recreate="always") as batch_op:
        batch_op.drop_column("deactivation_reason_encrypted")
        batch_op.drop_column("deactivated_at")
        batch_op.drop_column("is_active")
        batch_op.add_column(sa.Column("priority_order_text", sa.String(), nullable=True))

    op.execute(
        "UPDATE asset_beneficiaries "
        "SET priority_order_text = CAST(priority_order AS TEXT) "
        "WHERE priority_order IS NOT NULL"
    )

    with op.batch_alter_table("asset_beneficiaries", recreate="always") as batch_op:
        batch_op.drop_column("priority_order")
        batch_op.alter_column("priority_order_text", new_column_name="priority_order")
