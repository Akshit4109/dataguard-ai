"""Pydantic schemas for Data Health Score and Combined Report."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.anomaly import AnomalyDetectionReport
from app.schemas.profiling import DatasetProfile
from app.schemas.validation import ValidationReport


class HealthStatus(str, Enum):
    """Health classification levels based on overall quality score."""

    EXCELLENT = "EXCELLENT"          # 90 – 100
    GOOD = "GOOD"                    # 75 – 89
    NEEDS_ATTENTION = "NEEDS_ATTENTION"  # 50 – 74
    POOR = "POOR"                    # 0 – 49


class ReportSummary(BaseModel):
    """Concise numerical metrics summary across all analysis phases."""

    rows: int = Field(description="Total rows in the dataset")
    columns: int = Field(description="Total columns in the dataset")
    missing_values: int = Field(description="Total count of missing/null values")
    duplicates: int = Field(description="Total count of duplicate rows")
    validation_violations: int = Field(description="Total rule violations found during validation")
    anomalies: int = Field(description="Total records flagged as statistical anomalies")


class ScoreBreakdown(BaseModel):
    """Component scores contributing to the overall Data Health Score."""

    completeness_score: float = Field(description="Completeness quality score (0.0 to 100.0, weight: 30%)")
    validation_score: float = Field(description="Validation quality score (0.0 to 100.0, weight: 30%)")
    uniqueness_score: float = Field(description="Uniqueness quality score (0.0 to 100.0, weight: 20%)")
    anomaly_score: float = Field(description="Anomaly quality score (0.0 to 100.0, weight: 20%)")


class DataGuardReport(BaseModel):
    """Comprehensive combined report synthesizing profiling, validation, ML anomalies, and health scoring."""

    id: Optional[int] = Field(default=None, description="Unique Report ID in database")
    dataset_id: Optional[int] = Field(default=None, description="Unique Dataset ID in database")
    filename: Optional[str] = Field(default=None, description="Source CSV filename")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    health_score: float = Field(description="Overall Data Health Score (0.0 to 100.0)")
    status: HealthStatus = Field(description="Overall health rating (EXCELLENT, GOOD, NEEDS_ATTENTION, POOR)")
    summary: ReportSummary = Field(description="Summary metrics across all checks")
    score_breakdown: ScoreBreakdown = Field(description="Detailed breakdown of weighted score components")
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable rule-based data hygiene recommendations",
    )
    profile: Optional[DatasetProfile] = Field(
        default=None,
        description="Detailed statistical profiling report",
    )
    validation: Optional[ValidationReport] = Field(
        default=None,
        description="Detailed data quality validation report",
    )
    anomalies: Optional[AnomalyDetectionReport] = Field(
        default=None,
        description="Detailed ML anomaly detection report",
    )
