from __future__ import annotations

import logging

from sqlalchemy import Engine, inspect, text

from src.db.base import Base
from src.db import models as _models  # noqa: F401
from src.db.models.dataset_entry import DatasetEntry
from src.db.models.artifact import Artifact
from src.db.models.content_version import ContentVersion
from src.db.models.editorial_session import EditorialSession
from src.db.models.platform_output import PlatformOutput
from src.db.models.project import Project
from src.db.models.publish_job import PublishJob
from src.db.models.user import User
from src.db.models.user_context_memory import UserContextMemory
from src.db.models.voice_profile_collection import VoiceProfileCollection
from src.db.models.voice_profile_version import VoiceProfileVersion
from src.db.models.voice_profile_version_dataset import VoiceProfileVersionDataset
from src.db.session import get_engine

logger = logging.getLogger(__name__)

TARGET_TABLES = [
    User.__table__,
    Project.__table__,
    ContentVersion.__table__,
    PlatformOutput.__table__,
    PublishJob.__table__,
    Artifact.__table__,
    EditorialSession.__table__,
    UserContextMemory.__table__,
    VoiceProfileCollection.__table__,
    VoiceProfileVersion.__table__,
    VoiceProfileVersionDataset.__table__,
    DatasetEntry.__table__,
]


def _drop_public_tables(eng: Engine) -> int:
    insp = inspect(eng)
    tables = [t for t in insp.get_table_names(schema="public")]
    dropped = 0
    with eng.begin() as conn:
        for table in tables:
            conn.execute(text(f'DROP TABLE IF EXISTS public."{table}" CASCADE'))
            dropped += 1
    return dropped


def create_all(engine: Engine | None = None) -> None:
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng, tables=TARGET_TABLES)
    logger.info("DB create_all completed for target schema (dialect=%s)", eng.dialect.name)


def reset_schema(engine: Engine | None = None) -> None:
    eng = engine or get_engine()
    dropped = _drop_public_tables(eng)
    Base.metadata.create_all(bind=eng, tables=TARGET_TABLES)
    logger.info("DB schema reset completed (dropped=%s, dialect=%s)", dropped, eng.dialect.name)


