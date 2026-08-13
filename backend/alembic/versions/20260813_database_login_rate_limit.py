"""Add shared login failure rate-limit state.

Revision ID: e3f4a5b6c7d8
Revises: c1d2e3f4a5b6
Create Date: 2026-08-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e3f4a5b6c7d8"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_rate_limit_attempts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("client_key_hash", sa.String(length=64), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_login_rate_limit_attempts_client_key_hash",
        "login_rate_limit_attempts",
        ["client_key_hash"],
        unique=False,
    )
    op.create_index(
        "ix_login_rate_limit_attempts_attempted_at",
        "login_rate_limit_attempts",
        ["attempted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_login_rate_limit_attempts_attempted_at", table_name="login_rate_limit_attempts")
    op.drop_index("ix_login_rate_limit_attempts_client_key_hash", table_name="login_rate_limit_attempts")
    op.drop_table("login_rate_limit_attempts")
