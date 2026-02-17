from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy import text

from src.db.base import Base
from src.db import models as _models  # noqa: F401
from src.db.session import get_engine


def create_all(engine: Engine | None = None) -> None:
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)
    _ensure_columns(eng)


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
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

