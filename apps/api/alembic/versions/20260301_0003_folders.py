"""add folder organization for saved items/threads

Revision ID: 20260301_0003
Revises: 20260301_0002
Create Date: 2026-03-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260301_0003"
down_revision: str | None = "20260301_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "x_folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_x_folders_user_name"),
    )
    op.create_index("ix_x_folders_user_id", "x_folders", ["user_id"], unique=False)

    op.add_column("x_items", sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("x_threads", sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_x_items_folder_id", "x_items", ["folder_id"], unique=False)
    op.create_index("ix_x_threads_folder_id", "x_threads", ["folder_id"], unique=False)
    op.create_foreign_key(
        "fk_x_items_folder_id_x_folders",
        "x_items",
        "x_folders",
        ["folder_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_x_threads_folder_id_x_folders",
        "x_threads",
        "x_folders",
        ["folder_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_x_threads_folder_id_x_folders", "x_threads", type_="foreignkey")
    op.drop_constraint("fk_x_items_folder_id_x_folders", "x_items", type_="foreignkey")
    op.drop_index("ix_x_threads_folder_id", table_name="x_threads")
    op.drop_index("ix_x_items_folder_id", table_name="x_items")
    op.drop_column("x_threads", "folder_id")
    op.drop_column("x_items", "folder_id")

    op.drop_index("ix_x_folders_user_id", table_name="x_folders")
    op.drop_table("x_folders")
