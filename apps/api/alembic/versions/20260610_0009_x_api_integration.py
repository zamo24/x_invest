"""add official X API integration and verification metadata

Revision ID: 20260610_0009
Revises: 20260606_0008
Create Date: 2026-06-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260610_0009"
down_revision: str | None = "20260606_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("x_items", sa.Column("external_source", sa.String(length=30), server_default="x", nullable=False))
    op.add_column("x_items", sa.Column("external_id", sa.String(length=100), nullable=True))
    op.add_column(
        "x_items",
        sa.Column("content_status", sa.String(length=30), server_default="pending_verification", nullable=False),
    )
    op.add_column("x_items", sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("x_items", sa.Column("last_content_change_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("x_items", sa.Column("unavailable_reason", sa.Text(), nullable=True))
    op.create_index("ix_x_items_external_id", "x_items", ["external_id"], unique=False)
    op.create_index("ix_x_items_content_status", "x_items", ["content_status"], unique=False)
    op.execute("UPDATE x_items SET external_id = tweet_id")
    op.execute(
        """
        UPDATE x_items
        SET content_status = 'unsupported',
            unavailable_reason = 'Full-body X Article capture is unsupported by the official integration.'
        WHERE COALESCE(json_raw->>'source_kind', '') = 'article'
        """
    )

    op.create_table(
        "x_integrations",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("x_user_id", sa.String(length=64), nullable=False),
        sa.Column("x_username", sa.String(length=100), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="connected", nullable=False),
        sa.Column("bookmark_sync_cursor", sa.Text(), nullable=True),
        sa.Column("last_bookmark_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_bookmark_sync_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_x_integrations_x_user_id", "x_integrations", ["x_user_id"], unique=False)

    op.create_table(
        "x_oauth_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("pkce_verifier_encrypted", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_x_oauth_states_user_id", "x_oauth_states", ["user_id"], unique=False)
    op.create_index("ix_x_oauth_states_state_hash", "x_oauth_states", ["state_hash"], unique=True)
    op.create_index("ix_x_oauth_states_expires_at", "x_oauth_states", ["expires_at"], unique=False)

    op.create_table(
        "x_api_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("requested_post_count", sa.Integer(), nullable=False),
        sa.Column("returned_post_count", sa.Integer(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_x_api_usage_user_id", "x_api_usage", ["user_id"], unique=False)
    op.create_index("ix_x_api_usage_operation", "x_api_usage", ["operation"], unique=False)
    op.create_index("ix_x_api_usage_created_at", "x_api_usage", ["created_at"], unique=False)

    op.create_table(
        "x_bookmark_folder_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("x_folder_id", sa.String(length=100), nullable=False),
        sa.Column("x_folder_name", sa.String(length=200), nullable=False),
        sa.Column("local_folder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["local_folder_id"], ["x_folders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "x_folder_id", name="uq_x_bookmark_folder_mapping"),
    )
    op.create_index("ix_x_bookmark_folder_mappings_user_id", "x_bookmark_folder_mappings", ["user_id"], unique=False)
    op.create_index(
        "ix_x_bookmark_folder_mappings_local_folder_id",
        "x_bookmark_folder_mappings",
        ["local_folder_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_x_bookmark_folder_mappings_local_folder_id", table_name="x_bookmark_folder_mappings")
    op.drop_index("ix_x_bookmark_folder_mappings_user_id", table_name="x_bookmark_folder_mappings")
    op.drop_table("x_bookmark_folder_mappings")
    op.drop_index("ix_x_api_usage_created_at", table_name="x_api_usage")
    op.drop_index("ix_x_api_usage_operation", table_name="x_api_usage")
    op.drop_index("ix_x_api_usage_user_id", table_name="x_api_usage")
    op.drop_table("x_api_usage")
    op.drop_index("ix_x_oauth_states_expires_at", table_name="x_oauth_states")
    op.drop_index("ix_x_oauth_states_state_hash", table_name="x_oauth_states")
    op.drop_index("ix_x_oauth_states_user_id", table_name="x_oauth_states")
    op.drop_table("x_oauth_states")
    op.drop_index("ix_x_integrations_x_user_id", table_name="x_integrations")
    op.drop_table("x_integrations")
    op.drop_index("ix_x_items_content_status", table_name="x_items")
    op.drop_index("ix_x_items_external_id", table_name="x_items")
    op.drop_column("x_items", "unavailable_reason")
    op.drop_column("x_items", "last_content_change_at")
    op.drop_column("x_items", "last_verified_at")
    op.drop_column("x_items", "content_status")
    op.drop_column("x_items", "external_id")
    op.drop_column("x_items", "external_source")
