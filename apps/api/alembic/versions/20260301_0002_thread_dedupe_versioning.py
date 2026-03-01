"""thread dedupe/versioning support

Revision ID: 20260301_0002
Revises: 20260227_0001
Create Date: 2026-03-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260301_0002"
down_revision: str | None = "20260227_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "x_threads",
        sa.Column("capture_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.create_index("ix_x_threads_user_root_tweet_id", "x_threads", ["user_id", "root_tweet_id"], unique=False)
    op.create_index("ix_x_threads_user_root_url", "x_threads", ["user_id", "root_url"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_x_threads_user_root_url", table_name="x_threads")
    op.drop_index("ix_x_threads_user_root_tweet_id", table_name="x_threads")
    op.drop_column("x_threads", "capture_version")
