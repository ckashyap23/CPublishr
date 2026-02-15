from __future__ import annotations

from sqlalchemy import Engine

from src.db.base import Base
from src.db import models as _models  # noqa: F401
from src.db.session import get_engine


def create_all(engine: Engine | None = None) -> None:
    Base.metadata.create_all(bind=engine or get_engine())
