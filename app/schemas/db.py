"""Pydantic schemas for database persisted reports and listing."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.health import DataGuardReport, HealthStatus


class ReportListItem(BaseModel):
    """Concise item for listing saved reports."""

    id: int = Field(description="Unique report ID")
    dataset_id: int = Field(description="Associated dataset ID")
    filename: str = Field(description="Uploaded CSV filename")
    row_count: int = Field(description="Total rows analyzed")
    column_count: int = Field(description="Total columns analyzed")
    missing_values: int = Field(description="Total missing values")
    duplicate_rows: int = Field(description="Total duplicate rows")
    validation_violations: int = Field(description="Total validation rule violations")
    anomalies: int = Field(description="Total anomalous records")
    health_score: float = Field(description="Computed health score (0-100)")
    health_status: HealthStatus = Field(description="Health classification status")
    created_at: datetime = Field(description="Report creation timestamp")

    model_config = {"from_attributes": True}


class SavedReportResponse(BaseModel):
    """Complete retrieved or saved report response with database metadata."""

    id: int = Field(description="Report ID in database")
    dataset_id: int = Field(description="Dataset ID in database")
    filename: str = Field(description="Original filename")
    created_at: datetime = Field(description="Creation timestamp")
    report: DataGuardReport = Field(description="Complete DataGuard analysis report")
