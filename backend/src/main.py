import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.logging import configure_logging
from src.db.init_db import create_all

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
allowed_origins = [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
def _startup() -> None:
    if settings.db_auto_create:
        try:
            create_all()
        except Exception as exc:
            # Log but don't crash — DB may be temporarily unreachable at cold start.
            # Tables will be created on the next request that triggers a DB connection.
            logger.error("DB auto-create failed at startup (non-fatal): %s", exc)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
