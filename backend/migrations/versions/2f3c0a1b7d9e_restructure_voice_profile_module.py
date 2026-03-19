"""restructure_voice_profile_module

Revision ID: 2f3c0a1b7d9e
Revises: f8608937b0fb
Create Date: 2026-03-14 21:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2f3c0a1b7d9e"
down_revision: Union[str, Sequence[str], None] = "f8608937b0fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names(schema="public")


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(idx.get("name") == index_name for idx in inspector.get_indexes(table_name, schema="public"))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name, indexes in [
        ("voice_profile_version_datasets", []),
        ("voice_profile_versions", ["ix_voice_profile_versions_voice_profile_id"]),
        ("dataset_entries", ["ix_dataset_entries_dataset_id"]),
        ("voice_profile_datasets", ["ix_voice_profile_datasets_collection_id", "ix_voice_profile_datasets_user_id"]),
        ("voice_profile_collections", ["ix_voice_profile_collections_user_id"]),
        ("voice_profile_platforms", ["ix_voice_profile_platforms_voice_profile_id", "ix_voice_profile_platforms_user_id"]),
        ("voice_profiles", ["ix_voice_profiles_collection_id", "ix_voice_profiles_user_id", "ix_voice_profiles_voice_profile_id"]),
    ]:
        if _table_exists(inspector, table_name):
            for index_name in indexes:
                if _index_exists(inspector, table_name, index_name):
                    op.drop_index(index_name, table_name=table_name)
            op.drop_table(table_name)

    op.create_table(
        "voice_profile_collections",
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("collection_name", sa.Text(), nullable=False),
        sa.Column("platforms", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("collection_id"),
    )
    op.create_index("ix_voice_profile_collections_user_id", "voice_profile_collections", ["user_id"], unique=False)

    op.create_table(
        "voice_profile_datasets",
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_name", sa.Text(), nullable=False),
        sa.Column("source_profile", sa.Text(), nullable=True),
        sa.Column("blob_prefix", sa.Text(), nullable=False),
        sa.Column("sample_scope_note", sa.Text(), nullable=True),
        sa.Column("entry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["collection_id"], ["voice_profile_collections.collection_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("dataset_id"),
        sa.UniqueConstraint("collection_id", "dataset_name", name="uq_voice_profile_datasets_collection_name"),
    )
    op.create_index("ix_voice_profile_datasets_collection_id", "voice_profile_datasets", ["collection_id"], unique=False)
    op.create_index("ix_voice_profile_datasets_user_id", "voice_profile_datasets", ["user_id"], unique=False)

    op.create_table(
        "voice_profiles",
        sa.Column("voice_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("voice_profile_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["collection_id"], ["voice_profile_collections.collection_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("voice_profile_id"),
        sa.UniqueConstraint("collection_id", "voice_profile_name", name="uq_voice_profiles_collection_name"),
    )
    op.create_index("ix_voice_profiles_collection_id", "voice_profiles", ["collection_id"], unique=False)
    op.create_index("ix_voice_profiles_user_id", "voice_profiles", ["user_id"], unique=False)

    op.create_table(
        "voice_profile_versions",
        sa.Column("voice_profile_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voice_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("intended_use", sa.Text(), nullable=True),
        sa.Column("core_voice", sa.Text(), nullable=True),
        sa.Column("style_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tone_baseline", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("do_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dont_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_profile_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generation_status", sa.Text(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["voice_profile_id"], ["voice_profiles.voice_profile_id"]),
        sa.PrimaryKeyConstraint("voice_profile_version_id"),
        sa.UniqueConstraint("voice_profile_id", "version_no", name="uq_voice_profile_versions_profile_version_no"),
    )
    op.create_index("ix_voice_profile_versions_voice_profile_id", "voice_profile_versions", ["voice_profile_id"], unique=False)

    op.create_table(
        "voice_profile_version_datasets",
        sa.Column("voice_profile_version_dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voice_profile_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_name", sa.Text(), nullable=True),
        sa.Column("source_profile", sa.Text(), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("sample_scope_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["voice_profile_datasets.dataset_id"]),
        sa.ForeignKeyConstraint(["voice_profile_version_id"], ["voice_profile_versions.voice_profile_version_id"]),
        sa.PrimaryKeyConstraint("voice_profile_version_dataset_id"),
        sa.UniqueConstraint("voice_profile_version_id", "dataset_id", name="uq_voice_profile_version_datasets_version_dataset"),
    )

    op.create_table(
        "dataset_entries",
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("blob_uri", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("date_month_year", sa.Text(), nullable=True),
        sa.Column("text_clean", sa.Text(), nullable=True),
        sa.Column("reactions", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Integer(), nullable=True),
        sa.Column("total_visible", sa.Integer(), nullable=True),
        sa.Column("metadata_asset", sa.Text(), nullable=True),
        sa.Column("entry_type", sa.Text(), nullable=False),
        sa.Column("format_family", sa.Text(), nullable=True),
        sa.Column("hook_type", sa.Text(), nullable=True),
        sa.Column("cta_type", sa.Text(), nullable=True),
        sa.Column("cta_present", sa.Boolean(), nullable=True),
        sa.Column("theme_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "entry_type IN ('text_post','carousel','image_post','video','reel','short_video','podcast_clip','thread','email','blog_post','other')",
            name="ck_dataset_entries_entry_type",
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["voice_profile_datasets.dataset_id"]),
        sa.PrimaryKeyConstraint("entry_id"),
    )
    op.create_index("ix_dataset_entries_dataset_id", "dataset_entries", ["dataset_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name, indexes in [
        ("dataset_entries", ["ix_dataset_entries_dataset_id"]),
        ("voice_profile_version_datasets", []),
        ("voice_profile_versions", ["ix_voice_profile_versions_voice_profile_id"]),
        ("voice_profiles", ["ix_voice_profiles_collection_id", "ix_voice_profiles_user_id"]),
        ("voice_profile_datasets", ["ix_voice_profile_datasets_collection_id", "ix_voice_profile_datasets_user_id"]),
        ("voice_profile_collections", ["ix_voice_profile_collections_user_id"]),
    ]:
        if _table_exists(inspector, table_name):
            for index_name in indexes:
                if _index_exists(inspector, table_name, index_name):
                    op.drop_index(index_name, table_name=table_name)
            op.drop_table(table_name)

    op.create_table(
        "voice_profiles",
        sa.Column("voice_profile_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("rules_json", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name="fk_voice_profiles_user_id_users"),
        sa.PrimaryKeyConstraint("voice_profile_id"),
    )
    op.create_index("ix_voice_profiles_user_id", "voice_profiles", ["user_id"], unique=False)

    op.create_table(
        "voice_profile_platforms",
        sa.Column("row_id", sa.String(length=64), nullable=False),
        sa.Column("voice_profile_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name="fk_voice_profile_platforms_user_id_users"),
        sa.ForeignKeyConstraint(
            ["voice_profile_id"],
            ["voice_profiles.voice_profile_id"],
            name="fk_voice_profile_platforms_voice_profile_id_voice_profiles",
        ),
        sa.PrimaryKeyConstraint("row_id"),
    )
    op.create_index("ix_voice_profile_platforms_voice_profile_id", "voice_profile_platforms", ["voice_profile_id"], unique=False)
    op.create_index("ix_voice_profile_platforms_user_id", "voice_profile_platforms", ["user_id"], unique=False)

    op.create_table(
        "voice_profile_collections",
        sa.Column("voice_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("voice_profile_name", sa.Text(), nullable=False),
        sa.Column("platforms", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("voice_profile_id"),
    )
    op.create_index("ix_voice_profile_collections_user_id", "voice_profile_collections", ["user_id"], unique=False)

    op.create_table(
        "voice_profile_versions",
        sa.Column("voice_profile_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voice_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("intended_use", sa.Text(), nullable=True),
        sa.Column("core_voice", sa.Text(), nullable=True),
        sa.Column("style_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tone_baseline", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("do_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dont_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_profile_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generation_status", sa.Text(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["voice_profile_id"], ["voice_profile_collections.voice_profile_id"]),
        sa.PrimaryKeyConstraint("voice_profile_version_id"),
        sa.UniqueConstraint("voice_profile_id", "version_no", name="uq_voice_profile_versions_profile_version_no"),
    )
    op.create_index("ix_voice_profile_versions_voice_profile_id", "voice_profile_versions", ["voice_profile_id"], unique=False)

    op.create_table(
        "voice_profile_version_datasets",
        sa.Column("voice_profile_version_dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voice_profile_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_name", sa.Text(), nullable=True),
        sa.Column("source_profile", sa.Text(), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("sample_scope_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["voice_profile_version_id"], ["voice_profile_versions.voice_profile_version_id"]),
        sa.PrimaryKeyConstraint("voice_profile_version_dataset_id"),
        sa.UniqueConstraint("voice_profile_version_id", "dataset_id", name="uq_voice_profile_version_datasets_version_dataset"),
    )

    op.create_table(
        "dataset_entries",
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("blob_uri", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("date_month_year", sa.Text(), nullable=True),
        sa.Column("text_clean", sa.Text(), nullable=True),
        sa.Column("reactions", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Integer(), nullable=True),
        sa.Column("total_visible", sa.Integer(), nullable=True),
        sa.Column("metadata_asset", sa.Text(), nullable=True),
        sa.Column("entry_type", sa.Text(), nullable=False),
        sa.Column("format_family", sa.Text(), nullable=True),
        sa.Column("hook_type", sa.Text(), nullable=True),
        sa.Column("cta_type", sa.Text(), nullable=True),
        sa.Column("cta_present", sa.Boolean(), nullable=True),
        sa.Column("theme_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "entry_type IN ('text_post','carousel','image_post','video','reel','short_video','podcast_clip','thread','email','blog_post','other')",
            name="ck_dataset_entries_entry_type",
        ),
        sa.PrimaryKeyConstraint("entry_id"),
    )
    op.create_index("ix_dataset_entries_dataset_id", "dataset_entries", ["dataset_id"], unique=False)
