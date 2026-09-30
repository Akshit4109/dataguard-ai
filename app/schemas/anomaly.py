"""Pydantic schemas for ML Anomaly Detection results."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnomalyStatus(str, Enum):
    """Classification status for evaluated records."""

    NORMAL = "NORMAL"
    ANOMALY = "ANOMALY"


class AnomalyRecord(BaseModel):
    """Details of a record identified as anomalous or evaluated by the detector."""

    row_index: int = Field(description="Zero-based row index in the dataset")
    record_id: Optional[str] = Field(default=None, description="Identifier value if available (e.g. transaction_id)")
    anomaly_score: float = Field(
        description="Isolation Forest decision score (lower scores indicate higher abnormality)"
    )
    status: AnomalyStatus = Field(description="Classification status: NORMAL or ANOMALY")
    is_anomaly: bool = Field(description="True if record is flagged as anomalous")
    features: Dict[str, Any] = Field(
        default_factory=dict,
        description="Feature values used in anomaly evaluation",
    )


class AnomalyDetectionReport(BaseModel):
    """Comprehensive anomaly detection report returned by the API and engine."""

    total_records: int = Field(description="Total number of evaluated records")
    anomaly_count: int = Field(description="Number of detected anomalous records")
    anomaly_percentage: float = Field(description="Percentage of records classified as anomalies (0.0 to 100.0)")
    features_used: List[str] = Field(
        default_factory=list,
        description="List of numeric features utilized by the Isolation Forest model",
    )
    anomalies: List[AnomalyRecord] = Field(
        default_factory=list,
        description="List of detected anomalous records",
    )
