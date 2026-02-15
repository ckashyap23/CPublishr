from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.config import settings

engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, autocommit=False, future=True)


def init_engine() -> Engine:
    global engine, SessionLocal
    url = settings.database_url
    kwargs: dict = {"future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    SessionLocal.configure(bind=engine)
    return engine


def get_engine() -> Engine:
    if engine is None:
        return init_engine()
    return engine


init_engine()
