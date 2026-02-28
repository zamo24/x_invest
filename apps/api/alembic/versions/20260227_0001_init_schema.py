"""initial schema

Revision ID: 20260227_0001
Revises:
Create Date: 2026-02-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260227_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("clerk_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=True)

    op.create_table(
        "api_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_fingerprint", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_tokens_user_id", "api_tokens", ["user_id"], unique=False)
    op.create_index("ix_api_tokens_token_hash", "api_tokens", ["token_hash"], unique=True)

    op.create_table(
        "x_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tweet_id", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("author_handle", sa.String(length=100), nullable=False),
        sa.Column("author_name", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("quoted_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("json_raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("user_id", "tweet_id", name="uq_x_items_user_tweet"),
    )
    op.create_index("ix_x_items_user_id", "x_items", ["user_id"], unique=False)
    op.create_index("ix_x_items_hash", "x_items", ["hash"], unique=False)

    op.create_table(
        "x_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("root_tweet_id", sa.String(length=64), nullable=True),
        sa.Column("root_url", sa.String(length=500), nullable=True),
        sa.Column("title", sa.String(length=280), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_partial", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("partial_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_x_threads_user_id", "x_threads", ["user_id"], unique=False)

    op.create_table(
        "x_thread_items",
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("x_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("x_items.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("thread_id", "item_id"),
    )

    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding", Vector(256), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_chunks_user_id", "chunks", ["user_id"], unique=False)
    op.create_index("ix_chunks_source_type", "chunks", ["source_type"], unique=False)
    op.create_index("ix_chunks_source_id", "chunks", ["source_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chunks_source_id", table_name="chunks")
    op.drop_index("ix_chunks_source_type", table_name="chunks")
    op.drop_index("ix_chunks_user_id", table_name="chunks")
    op.drop_table("chunks")

    op.drop_table("x_thread_items")

    op.drop_index("ix_x_threads_user_id", table_name="x_threads")
    op.drop_table("x_threads")

    op.drop_index("ix_x_items_hash", table_name="x_items")
    op.drop_index("ix_x_items_user_id", table_name="x_items")
    op.drop_table("x_items")

    op.drop_index("ix_api_tokens_token_hash", table_name="api_tokens")
    op.drop_index("ix_api_tokens_user_id", table_name="api_tokens")
    op.drop_table("api_tokens")

    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_table("users")
