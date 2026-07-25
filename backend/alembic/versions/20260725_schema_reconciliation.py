"""Reconcile Alembic schema with registered SQLAlchemy models.

Revision ID: f1a2b3c4d5e6
Revises: e4c7a9b2d611
Create Date: 2026-07-25 06:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "e4c7a9b2d611"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("token_identifier", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_info", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sessions_id"), "sessions", ["id"], unique=False)
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_sessions_token_identifier"),
        "sessions",
        ["token_identifier"],
        unique=True,
    )

    op.create_table(
        "user_security_settings",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False),
        sa.Column("mfa_method", sa.String(), nullable=True),
        sa.Column("recovery_codes", sa.Text(), nullable=True),
        sa.Column("security_preferences", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_user_security_settings_user_id"),
        "user_security_settings",
        ["user_id"],
        unique=False,
    )

    with op.batch_alter_table("beneficiaries", recreate="always") as batch_op:
        batch_op.alter_column("relationship", new_column_name="relationship_type")


def downgrade() -> None:
    with op.batch_alter_table("beneficiaries", recreate="always") as batch_op:
        batch_op.alter_column("relationship_type", new_column_name="relationship")

    op.drop_index(
        op.f("ix_user_security_settings_user_id"),
        table_name="user_security_settings",
    )
    op.drop_table("user_security_settings")
    op.drop_index(op.f("ix_sessions_token_identifier"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_id"), table_name="sessions")
    op.drop_table("sessions")
