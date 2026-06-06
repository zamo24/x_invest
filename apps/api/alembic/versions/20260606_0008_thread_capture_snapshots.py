"""add immutable thread capture snapshots

Revision ID: 20260606_0008
Revises: 20260302_0007
Create Date: 2026-06-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260606_0008"
down_revision: str | None = "20260302_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "x_thread_captures",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capture_version", sa.Integer(), nullable=False),
        sa.Column("root_tweet_id", sa.String(length=64), nullable=True),
        sa.Column("root_url", sa.String(length=500), nullable=True),
        sa.Column("title", sa.String(length=280), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_partial", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("partial_reason", sa.Text(), nullable=True),
        sa.Column("macro_chunk_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["x_threads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", "capture_version", name="uq_x_thread_captures_thread_version"),
    )
    op.create_index("ix_x_thread_captures_thread_id", "x_thread_captures", ["thread_id"], unique=False)
    op.create_index("ix_x_thread_captures_user_id", "x_thread_captures", ["user_id"], unique=False)

    op.create_table(
        "x_thread_capture_items",
        sa.Column("capture_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_order", sa.Integer(), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["capture_id"], ["x_thread_captures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["x_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("capture_id", "item_order"),
    )
    op.create_index("ix_x_thread_capture_items_item_id", "x_thread_capture_items", ["item_id"], unique=False)

    op.execute(
        """
        INSERT INTO x_thread_captures (
            id, thread_id, user_id, capture_version, root_tweet_id, root_url,
            title, captured_at, is_partial, partial_reason, macro_chunk_text
        )
        SELECT
            gen_random_uuid(), t.id, t.user_id, t.capture_version, t.root_tweet_id,
            t.root_url, t.title, t.captured_at, t.is_partial, t.partial_reason, c.chunk_text
        FROM x_threads t
        LEFT JOIN LATERAL (
            SELECT chunk_text
            FROM chunks
            WHERE user_id = t.user_id
              AND source_type = 'x_thread'
              AND source_id = t.id
              AND chunk_order = 0
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        ) c ON true
        """
    )
    op.execute(
        """
        INSERT INTO x_thread_capture_items (
            capture_id, item_order, item_id, tweet_id, url, author_handle,
            author_name, created_at, captured_at, text, quoted_json, json_raw, hash
        )
        SELECT
            capture.id,
            row_number() OVER (
                PARTITION BY ti.thread_id
                ORDER BY item.captured_at ASC, item.id ASC
            ) - 1,
            item.id,
            item.tweet_id,
            item.url,
            item.author_handle,
            item.author_name,
            item.created_at,
            item.captured_at,
            item.text,
            item.quoted_json,
            item.json_raw,
            item.hash
        FROM x_thread_items ti
        JOIN x_items item ON item.id = ti.item_id
        JOIN x_thread_captures capture
          ON capture.thread_id = ti.thread_id
         AND capture.capture_version = (
             SELECT capture_version FROM x_threads WHERE id = ti.thread_id
         )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_x_thread_capture_items_item_id", table_name="x_thread_capture_items")
    op.drop_table("x_thread_capture_items")
    op.drop_index("ix_x_thread_captures_user_id", table_name="x_thread_captures")
    op.drop_index("ix_x_thread_captures_thread_id", table_name="x_thread_captures")
    op.drop_table("x_thread_captures")
