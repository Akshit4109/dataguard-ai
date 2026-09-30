"""API package containing endpoints and routers for DataGuard AI."""

from app.api.anomalies import router as anomalies_router
from app.api.profile import router as profile_router
from app.api.report import router as report_router
from app.api.validate import router as validate_router

__all__ = ["profile_router", "validate_router", "anomalies_router", "report_router"]
