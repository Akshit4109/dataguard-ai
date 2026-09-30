"""API endpoints for Machine Learning Anomaly Detection."""

import io
from fastapi import APIRouter, File, HTTPException, UploadFile, status
import pandas as pd

from app.core.anomaly_detector import AnomalyDetector
from app.core.logging import get_logger
from app.schemas.anomaly import AnomalyDetectionReport

logger = get_logger(__name__)

router = APIRouter(tags=["Anomaly Detection"])


@router.post(
    "/anomalies",
    response_model=AnomalyDetectionReport,
    summary="Detect Anomalous Records using Isolation Forest",
    description=(
        "Upload a CSV dataset to run unsupervised ML anomaly detection (Isolation Forest) "
        "on numeric features. Returns summary statistics and detected anomalous records."
    ),
    status_code=status.HTTP_200_OK,
)
async def detect_dataset_anomalies(
    file: UploadFile = File(..., description="CSV file to analyze for anomalies"),
) -> AnomalyDetectionReport:
    """Analyze an uploaded CSV dataset for statistical anomalies using Isolation Forest."""
    # 1. Validate file extension
    if file.filename and not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a .csv extension.",
        )

    # 2. Read file contents
    try:
        contents = await file.read()
    except Exception as err:
        logger.error("Failed to read uploaded file: %s", err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the uploaded file.",
        )

    if not contents or not contents.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded CSV file is empty.",
        )

    # 3. Parse CSV with Pandas
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded CSV file contains no data or columns.",
        )
    except (pd.errors.ParserError, UnicodeDecodeError) as parse_err:
        logger.warning("CSV parse error: %s", parse_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV format: {str(parse_err)}",
        )
    except Exception as err:
        logger.error("Unexpected error parsing CSV: %s", err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to parse the CSV file. Please ensure it is a valid, well-formed CSV file.",
        )

    if len(df.columns) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded dataset contains no columns.",
        )

    # 4. Run Anomaly Detection Engine
    try:
        detector = AnomalyDetector()
        report = detector.detect_anomalies(df)
        logger.info(
            "Anomaly detection completed for '%s' (%d records, %d anomalies, features=%s)",
            file.filename,
            report.total_records,
            report.anomaly_count,
            report.features_used,
        )
        return report
    except ValueError as val_err:
        logger.warning("Validation error during anomaly detection: %s", val_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as err:
        logger.error("Anomaly detection execution error: %s", err, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while executing anomaly detection.",
        )
