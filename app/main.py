"""DataGuard AI — Main FastAPI Application Entrypoint."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI

from app.api.anomalies import router as anomalies_router
from app.api.profile import router as profile_router
from app.api.report import router as report_router
from app.api.validate import router as validate_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.database import init_db

# Initialize logging
setup_logging(log_level=settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager handling startup and shutdown events."""
    logger.info("Starting %s v%s in [%s] environment", settings.APP_NAME, settings.APP_VERSION, settings.APP_ENV)
    init_db()
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Data Quality & Anomaly Detection Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Register API routers
app.include_router(profile_router)
app.include_router(validate_router)
app.include_router(anomalies_router)
app.include_router(report_router)


@app.get("/", tags=["General"])
async def root() -> Dict[str, Any]:
    """Root endpoint verifying that DataGuard AI is operational."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "status": "online",
        "message": "Welcome to DataGuard AI — Data Quality & Anomaly Detection Platform",
    }


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring service status."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
    }
