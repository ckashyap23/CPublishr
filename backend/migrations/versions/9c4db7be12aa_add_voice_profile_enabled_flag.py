"""add_voice_profile_enabled_flag

Revision ID: 9c4db7be12aa
Revises: 2f3c0a1b7d9e
Create Date: 2026-03-15 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c4db7be12aa"
down_revision: Union[str, Sequence[str], None] = "2f3c0a1b7d9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("voice_profiles", schema="public")}
    if "is_enabled" not in columns:
        op.add_column(
            "voice_profiles",
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("voice_profiles", schema="public")}
    if "is_enabled" in columns:
        op.drop_column("voice_profiles", "is_enabled")
