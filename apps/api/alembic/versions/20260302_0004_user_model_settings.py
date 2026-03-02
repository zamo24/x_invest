"""add per-user model settings and byok key storage

Revision ID: 20260302_0004
Revises: 20260301_0003
Create Date: 2026-03-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260302_0004"
down_revision: str | None = "20260301_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_model_settings",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("inference_mode", sa.String(length=20), nullable=False, server_default="hosted"),
        sa.Column("preferred_provider", sa.String(length=50), nullable=False, server_default="openai"),
        sa.Column("preferred_model", sa.String(length=120), nullable=True),
        sa.Column("byo_openai_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("byo_openai_api_key_last4", sa.String(length=4), nullable=True),
        sa.Column("byo_openai_api_key_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_check_constraint(
        "ck_user_model_settings_inference_mode",
        "user_model_settings",
        "inference_mode in ('hosted', 'byok')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_user_model_settings_inference_mode", "user_model_settings", type_="check")
    op.drop_table("user_model_settings")
