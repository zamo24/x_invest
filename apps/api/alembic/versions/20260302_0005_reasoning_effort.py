"""add reasoning effort to user model settings

Revision ID: 20260302_0005
Revises: 20260302_0004
Create Date: 2026-03-02 00:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260302_0005"
down_revision: str | None = "20260302_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_model_settings",
        sa.Column("reasoning_effort", sa.String(length=20), nullable=False, server_default="medium"),
    )
    op.create_check_constraint(
        "ck_user_model_settings_reasoning_effort",
        "user_model_settings",
        "reasoning_effort in ('none', 'minimal', 'low', 'medium', 'high', 'xhigh')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_user_model_settings_reasoning_effort", "user_model_settings", type_="check")
    op.drop_column("user_model_settings", "reasoning_effort")
