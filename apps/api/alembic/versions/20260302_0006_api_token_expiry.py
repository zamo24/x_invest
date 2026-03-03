"""add optional api token expiration

Revision ID: 20260302_0006
Revises: 20260302_0005
Create Date: 2026-03-02 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260302_0006"
down_revision: str | None = "20260302_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("api_tokens", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_api_tokens_expires_at", "api_tokens", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_api_tokens_expires_at", table_name="api_tokens")
    op.drop_column("api_tokens", "expires_at")
