"""drop_users_name_column

Revision ID: f8608937b0fb
Revises: 870b136e1c9e
Create Date: 2026-02-21 14:26:43.252706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8608937b0fb'
down_revision: Union[str, Sequence[str], None] = '870b136e1c9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    exists = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='users' AND column_name='name' LIMIT 1"
        )
    ).first()
    if exists:
        op.drop_column("users", "name")


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    exists = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='users' AND column_name='name' LIMIT 1"
        )
    ).first()
    if not exists:
        op.add_column("users", sa.Column("name", sa.String(length=120), nullable=True))
        op.execute(sa.text("UPDATE users SET name = 'User' WHERE name IS NULL"))
        op.alter_column("users", "name", nullable=False)
