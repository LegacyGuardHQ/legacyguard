"""Initial LegacyGuard data model

Revision ID: 3f4afebac2b9
Revises: 
Create Date: 2026-07-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "3f4afebac2b9"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_event_type"), "audit_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)

    op.create_table(
        "assets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("asset_category", sa.String(), nullable=False),
        sa.Column("asset_name", sa.String(), nullable=False),
        sa.Column("institution", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("estimated_value", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("ownership_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assets_asset_category"), "assets", ["asset_category"], unique=False)
    op.create_index(op.f("ix_assets_asset_name"), "assets", ["asset_name"], unique=False)
    op.create_index(op.f("ix_assets_id"), "assets", ["id"], unique=False)
    op.create_index(op.f("ix_assets_user_id"), "assets", ["user_id"], unique=False)

    op.create_table(
        "asset_details",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("account_number_encrypted", sa.Text(), nullable=True),
        sa.Column("policy_number_encrypted", sa.Text(), nullable=True),
        sa.Column("login_information_reference", sa.Text(), nullable=True),
        sa.Column("contact_information", sa.Text(), nullable=True),
        sa.Column("notes_encrypted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_asset_details_asset_id"), "asset_details", ["asset_id"], unique=True)
    op.create_index(op.f("ix_asset_details_id"), "asset_details", ["id"], unique=False)

    op.create_table(
        "beneficiaries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("relationship", sa.String(), nullable=True),
        sa.Column("contact_information", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_beneficiaries_id"), "beneficiaries", ["id"], unique=False)
    op.create_index(op.f("ix_beneficiaries_name"), "beneficiaries", ["name"], unique=False)
    op.create_index(op.f("ix_beneficiaries_user_id"), "beneficiaries", ["user_id"], unique=False)

    op.create_table(
        "asset_beneficiaries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("beneficiary_id", sa.String(), nullable=False),
        sa.Column("percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("transfer_priority", sa.String(), nullable=True),
        sa.Column("transfer_method", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["beneficiaries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_asset_beneficiaries_asset_id"), "asset_beneficiaries", ["asset_id"], unique=False)
    op.create_index(op.f("ix_asset_beneficiaries_beneficiary_id"), "asset_beneficiaries", ["beneficiary_id"], unique=False)
    op.create_index(op.f("ix_asset_beneficiaries_id"), "asset_beneficiaries", ["id"], unique=False)

    op.create_table(
        "documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=True),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("document_name", sa.String(), nullable=False),
        sa.Column("storage_reference", sa.Text(), nullable=True),
        sa.Column("encrypted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_asset_id"), "documents", ["asset_id"], unique=False)
    op.create_index(op.f("ix_documents_document_name"), "documents", ["document_name"], unique=False)
    op.create_index(op.f("ix_documents_document_type"), "documents", ["document_type"], unique=False)
    op.create_index(op.f("ix_documents_id"), "documents", ["id"], unique=False)
    op.create_index(op.f("ix_documents_user_id"), "documents", ["user_id"], unique=False)

    op.create_table(
        "important_contacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("organization", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_important_contacts_id"), "important_contacts", ["id"], unique=False)
    op.create_index(op.f("ix_important_contacts_name"), "important_contacts", ["name"], unique=False)
    op.create_index(op.f("ix_important_contacts_user_id"), "important_contacts", ["user_id"], unique=False)

    op.create_table(
        "legacy_tasks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("task_name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_legacy_tasks_id"), "legacy_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_legacy_tasks_task_name"), "legacy_tasks", ["task_name"], unique=False)
    op.create_index(op.f("ix_legacy_tasks_user_id"), "legacy_tasks", ["user_id"], unique=False)

    op.create_table(
        "legacy_reports",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_legacy_reports_id"), "legacy_reports", ["id"], unique=False)
    op.create_index(op.f("ix_legacy_reports_report_type"), "legacy_reports", ["report_type"], unique=False)
    op.create_index(op.f("ix_legacy_reports_user_id"), "legacy_reports", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("legacy_reports")
    op.drop_table("legacy_tasks")
    op.drop_table("important_contacts")
    op.drop_table("documents")
    op.drop_table("asset_beneficiaries")
    op.drop_table("beneficiaries")
    op.drop_table("asset_details")
    op.drop_table("assets")
    op.drop_table("audit_logs")
    op.drop_table("users")
