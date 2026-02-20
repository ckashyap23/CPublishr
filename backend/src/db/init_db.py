from __future__ import annotations

import logging

from sqlalchemy import Engine

from src.db.base import Base
from src.db import models as _models  # noqa: F401
from src.db.session import get_engine

logger = logging.getLogger(__name__)


def create_all(engine: Engine | None = None) -> None:
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)
    logger.info("DB create_all completed (dialect=%s)", eng.dialect.name)

