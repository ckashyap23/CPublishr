"""multi_tenant_auth_schema

Revision ID: 870b136e1c9e
Revises:
Create Date: 2026-02-21 13:19:46.764076
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "870b136e1c9e"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table: str) -> bool:
    return table in inspector.get_table_names(schema="public")


def _column_exists(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(c.get("name") == column for c in inspector.get_columns(table, schema="public"))


def _index_exists(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(i.get("name") == name for i in inspector.get_indexes(table, schema="public"))


def _fk_exists(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(fk.get("name") == name for fk in inspector.get_foreign_keys(table, schema="public"))


def _fk_user_to_users_exists(inspector: sa.Inspector, table: str) -> bool:
    for fk in inspector.get_foreign_keys(table, schema="public"):
        constrained = fk.get("constrained_columns") or []
        referred_table = fk.get("referred_table")
        referred_columns = fk.get("referred_columns") or []
        if constrained == ["user_id"] and referred_table == "users" and referred_columns == ["user_id"]:
            return True
    return False


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not _table_exists(inspector, "users"):
        op.create_table(
            "users",
            sa.Column("user_id", sa.String(length=64), primary_key=True, nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("password_hash", sa.String(length=512), nullable=False),
            sa.UniqueConstraint("email", name="uq_users_email"),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    inspector = sa.inspect(conn)
    if _table_exists(inspector, "users"):
        if not _column_exists(inspector, "users", "name"):
            op.add_column("users", sa.Column("name", sa.String(length=120), nullable=True))
        if not _column_exists(inspector, "users", "password_hash"):
            op.add_column("users", sa.Column("password_hash", sa.String(length=512), nullable=True))
        if _column_exists(inspector, "users", "name"):
            op.execute(sa.text("UPDATE users SET name = 'User' WHERE name IS NULL"))
            op.alter_column("users", "name", nullable=False)
        if _column_exists(inspector, "users", "password_hash"):
            # pbkdf2_sha256 hash for placeholder password "changeme"
            conn.execute(
                sa.text("UPDATE users SET password_hash = :h WHERE password_hash IS NULL"),
                {"h": "pbkdf2_sha256$210000$T9r6mK/txvM+3W2IShZsKg==$3WNv8oS3R4xvJx9vV0+XQf8Vh4IcaM0qW4CNfJx4+2w="},
            )
            op.alter_column("users", "password_hash", nullable=False)
        if _column_exists(inspector, "users", "created_at"):
            op.execute(sa.text("UPDATE users SET created_at = now() WHERE created_at IS NULL"))
            op.alter_column("users", "created_at", nullable=False)
        if not _index_exists(inspector, "users", "ix_users_email"):
            op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Ensure there is at least one user for backfills.
    user_count = conn.execute(sa.text("SELECT COUNT(1) FROM users")).scalar_one()
    if int(user_count or 0) == 0:
        conn.execute(
            sa.text(
                "INSERT INTO users (user_id, email, created_at, name, password_hash) "
                "VALUES ('usr_legacy', 'legacy@example.local', now(), 'Legacy User', :h)"
            ),
            {"h": "pbkdf2_sha256$210000$T9r6mK/txvM+3W2IShZsKg==$3WNv8oS3R4xvJx9vV0+XQf8Vh4IcaM0qW4CNfJx4+2w="},
        )

    if not _table_exists(inspector, "voice_profiles"):
        op.create_table(
            "voice_profiles",
            sa.Column("voice_profile_id", sa.String(length=64), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.String(length=1000), nullable=True),
            sa.Column("rules_json", sa.JSON(), nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name="fk_voice_profiles_user_id_users"),
        )
        op.create_index("ix_voice_profiles_user_id", "voice_profiles", ["user_id"], unique=False)

    inspector = sa.inspect(conn)
    if not _table_exists(inspector, "voice_profile_platforms"):
        op.create_table(
            "voice_profile_platforms",
            sa.Column("row_id", sa.String(length=64), primary_key=True, nullable=False),
            sa.Column("voice_profile_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("platform", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(
                ["voice_profile_id"],
                ["voice_profiles.voice_profile_id"],
                name="fk_voice_profile_platforms_voice_profile_id_voice_profiles",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name="fk_voice_profile_platforms_user_id_users"),
        )
        op.create_index("ix_voice_profile_platforms_voice_profile_id", "voice_profile_platforms", ["voice_profile_id"], unique=False)
        op.create_index("ix_voice_profile_platforms_user_id", "voice_profile_platforms", ["user_id"], unique=False)

    inspector = sa.inspect(conn)
    if not _table_exists(inspector, "user_context_memory"):
        op.create_table(
            "user_context_memory",
            sa.Column("memory_id", sa.String(length=64), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("last_project_id", sa.String(length=64), nullable=True),
            sa.Column("last_view", sa.String(length=64), nullable=True),
            sa.Column("state_json", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name="fk_user_context_memory_user_id_users"),
        )
        op.create_index("ix_user_context_memory_user_id", "user_context_memory", ["user_id"], unique=True)

    inspector = sa.inspect(conn)
    tenant_tables = [
        "projects",
        "content_versions",
        "artifacts",
        "platform_outputs",
        "publish_jobs",
        "editorial_sessions",
        "voice_profiles",
        "voice_profile_platforms",
        "user_context_memory",
    ]

    default_user_id = conn.execute(sa.text("SELECT user_id FROM users ORDER BY created_at ASC NULLS LAST, user_id ASC LIMIT 1")).scalar_one()

    for table in tenant_tables:
        inspector = sa.inspect(conn)
        if not _table_exists(inspector, table):
            continue
        if not _column_exists(inspector, table, "user_id"):
            op.add_column(table, sa.Column("user_id", sa.String(length=64), nullable=True))
        conn.execute(sa.text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"), {"uid": default_user_id})
        op.alter_column(table, "user_id", nullable=False)

        inspector = sa.inspect(conn)
        idx_name = f"ix_{table}_user_id"
        if not _index_exists(inspector, table, idx_name):
            op.create_index(idx_name, table, ["user_id"], unique=False)
        fk_name = f"fk_{table}_user_id_users"
        if not _fk_exists(inspector, table, fk_name) and not _fk_user_to_users_exists(inspector, table):
            op.create_foreign_key(fk_name, table, "users", ["user_id"], ["user_id"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    tenant_tables = [
        "projects",
        "content_versions",
        "artifacts",
        "platform_outputs",
        "publish_jobs",
        "editorial_sessions",
    ]
    for table in tenant_tables:
        inspector = sa.inspect(conn)
        if not _table_exists(inspector, table):
            continue
        fk_name = f"fk_{table}_user_id_users"
        if _fk_exists(inspector, table, fk_name):
            op.drop_constraint(fk_name, table, type_="foreignkey")
        idx_name = f"ix_{table}_user_id"
        if _index_exists(inspector, table, idx_name):
            op.drop_index(idx_name, table_name=table)
        if _column_exists(inspector, table, "user_id"):
            op.drop_column(table, "user_id")

    inspector = sa.inspect(conn)
    if _table_exists(inspector, "voice_profile_platforms"):
        if _index_exists(inspector, "voice_profile_platforms", "ix_voice_profile_platforms_user_id"):
            op.drop_index("ix_voice_profile_platforms_user_id", table_name="voice_profile_platforms")
        op.drop_table("voice_profile_platforms")
    if _table_exists(inspector, "voice_profiles"):
        if _index_exists(inspector, "voice_profiles", "ix_voice_profiles_user_id"):
            op.drop_index("ix_voice_profiles_user_id", table_name="voice_profiles")
        op.drop_table("voice_profiles")
    if _table_exists(inspector, "user_context_memory"):
        if _index_exists(inspector, "user_context_memory", "ix_user_context_memory_user_id"):
            op.drop_index("ix_user_context_memory_user_id", table_name="user_context_memory")
        op.drop_table("user_context_memory")

    inspector = sa.inspect(conn)
    if _table_exists(inspector, "users"):
        if _index_exists(inspector, "users", "ix_users_email"):
            op.drop_index("ix_users_email", table_name="users")
        op.drop_table("users")
