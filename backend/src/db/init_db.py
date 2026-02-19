from __future__ import annotations

import logging

from sqlalchemy import Engine
from sqlalchemy import text

from src.db.base import Base
from src.db import models as _models  # noqa: F401
from src.db.session import get_engine

logger = logging.getLogger(__name__)


def create_all(engine: Engine | None = None) -> None:
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)
    logger.info("DB create_all completed (dialect=%s)", eng.dialect.name)
    _ensure_columns(eng)
    logger.info("DB compatibility patching completed")


def _ensure_columns(engine: Engine) -> None:
    # Lightweight compatibility patching for existing Postgres DBs.
    if engine.dialect.name != "postgresql":
        return
    statements = [
        "ALTER TABLE content_versions ADD COLUMN IF NOT EXISTS keywords_json TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE content_versions ADD COLUMN IF NOT EXISTS structure_outline_json TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE content_versions ADD COLUMN IF NOT EXISTS version_stage VARCHAR(32) NOT NULL DEFAULT 'draft'",
        "ALTER TABLE content_versions ADD COLUMN IF NOT EXISTS source_version_number INTEGER NULL",
        "ALTER TABLE content_versions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS final_version_number INTEGER NULL",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS finalized_at TIMESTAMP NULL",
        "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS format VARCHAR(64)",
        "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS kind VARCHAR(16)",
        "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS payload_json JSON NOT NULL DEFAULT '{}'::json",
        "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS tags_json JSON NOT NULL DEFAULT '[]'::json",
        "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'generated'",
        "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS parent_artifact_id VARCHAR(64) NULL",
        "ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

        schemas = list(
            conn.execute(
                text(
                    """
SELECT table_schema
FROM information_schema.tables
WHERE table_name = 'artifacts'
  AND table_type = 'BASE TABLE'
"""
                )
            ).scalars()
        )
        if not schemas:
            return

        def _qident(name: str) -> str:
            return '"' + str(name).replace('"', '""') + '"'

        for schema in schemas:
            tbl = f"{_qident(schema)}.{_qident('artifacts')}"
            logger.info("Applying artifacts compatibility patch for schema=%s", schema)

            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS format VARCHAR(64)"))
            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS kind VARCHAR(16)"))
            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS payload_json JSON NOT NULL DEFAULT '{{}}'::json"))
            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS tags_json JSON NOT NULL DEFAULT '[]'::json"))
            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'generated'"))
            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1"))
            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS parent_artifact_id VARCHAR(64) NULL"))
            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()"))

            col_types = {
                str(row[0]): str(row[1]).lower()
                for row in conn.execute(
                    text(
                        """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = :schema
  AND table_name = 'artifacts'
"""
                    ),
                    {"schema": schema},
                ).all()
            }

            # Force payload/tags to JSON type; no legacy data migration.
            if col_types.get("payload_json") != "json":
                conn.execute(text(f"ALTER TABLE {tbl} ALTER COLUMN payload_json DROP DEFAULT"))
                conn.execute(text(f"UPDATE {tbl} SET payload_json = '{{}}' WHERE payload_json IS NULL"))
                conn.execute(text(f"ALTER TABLE {tbl} ALTER COLUMN payload_json TYPE JSON USING '{{}}'::json"))
            if col_types.get("tags_json") != "json":
                conn.execute(text(f"ALTER TABLE {tbl} ALTER COLUMN tags_json DROP DEFAULT"))
                conn.execute(text(f"UPDATE {tbl} SET tags_json = '[]' WHERE tags_json IS NULL"))
                conn.execute(text(f"ALTER TABLE {tbl} ALTER COLUMN tags_json TYPE JSON USING '[]'::json"))
            conn.execute(text(f"ALTER TABLE {tbl} ALTER COLUMN payload_json SET DEFAULT '{{}}'::json"))
            conn.execute(text(f"ALTER TABLE {tbl} ALTER COLUMN tags_json SET DEFAULT '[]'::json"))

            conn.execute(text(f"UPDATE {tbl} SET format = COALESCE(format, 'blog_long')"))

            # Drop legacy columns that are not part of the new artifact schema.
            conn.execute(text(f"ALTER TABLE {tbl} DROP COLUMN IF EXISTS artifact_type"))
            conn.execute(text(f"ALTER TABLE {tbl} DROP COLUMN IF EXISTS content"))
            conn.execute(text(f"ALTER TABLE {tbl} DROP COLUMN IF EXISTS metadata_json"))
            conn.execute(text(f"ALTER TABLE {tbl} DROP COLUMN IF EXISTS artifact_url"))

            conn.execute(
                text(
                    f"""
UPDATE {tbl}
SET kind = COALESCE(
  kind,
  CASE
    WHEN COALESCE(format, 'blog_long') IN ('storyboard','shotlist','video','reel','short_video') THEN 'video'
    WHEN COALESCE(format, 'blog_long') IN ('voiceover','audio','voice_over_clip') THEN 'audio'
    WHEN COALESCE(format, 'blog_long') IN ('image','thumbnail','cover','image_prompt_pack') THEN 'image'
    WHEN COALESCE(format, 'blog_long') IN ('gif_loop','gif') THEN 'gif'
    WHEN COALESCE(format, 'blog_long') = 'bundle' THEN 'bundle'
    ELSE 'text'
  END
)
"""
                )
            )
            conn.execute(text(f"ALTER TABLE {tbl} ALTER COLUMN format SET NOT NULL"))
            conn.execute(text(f"ALTER TABLE {tbl} ALTER COLUMN kind SET NOT NULL"))
            conn.execute(
                text(
                    f"""
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ck_artifacts_kind'
      AND conrelid = '{schema}.artifacts'::regclass
  ) THEN
    ALTER TABLE {tbl}
      ADD CONSTRAINT ck_artifacts_kind
      CHECK (kind IN ('text','image','video','audio','gif','bundle'));
  END IF;
END $$;
"""
                )
            )

