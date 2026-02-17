from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.logging import configure_logging
from src.db.init_db import create_all

configure_logging()

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
    # Uses DATABASE_URL from .env (Postgres in your setup).
    if settings.db_auto_create:
        create_all()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
