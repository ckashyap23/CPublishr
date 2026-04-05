import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError

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


@app.exception_handler(OperationalError)
def handle_db_operational_error(_: Request, exc: OperationalError) -> JSONResponse:
    logger.error("Database connection failed during request: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database is unavailable. Check DATABASE_URL/network access and try again."},
    )


@app.exception_handler(SQLAlchemyError)
def handle_sqlalchemy_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("Database request failed: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database request failed."},
    )


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
