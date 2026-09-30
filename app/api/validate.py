"""API endpoints for Data Quality Validation."""

import io
from fastapi import APIRouter, File, HTTPException, UploadFile, status
import pandas as pd

from app.core.logging import get_logger
from app.core.validator import DataValidator
from app.schemas.validation import ValidationReport

logger = get_logger(__name__)

router = APIRouter(tags=["Validation"])


@router.post(
    "/validate",
    response_model=ValidationReport,
    summary="Validate a CSV Dataset",
    description=(
        "Upload a CSV file to evaluate data quality against defined rules "
        "(required fields, uniqueness, numeric ranges, allowed values, and schema checks)."
    ),
    status_code=status.HTTP_200_OK,
)
async def validate_dataset(
    file: UploadFile = File(..., description="CSV file to validate"),
) -> ValidationReport:
    """Validate data quality for an uploaded CSV dataset."""
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

    # 4. Run validation engine
    try:
        validator = DataValidator()
        report = validator.validate(df)
        logger.info(
            "Validation completed for dataset '%s' (is_valid=%s, failed_rules=%d)",
            file.filename,
            report.is_valid,
            report.failed_rules,
        )
        return report
    except Exception as err:
        logger.error("Validation execution error: %s", err, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while validating the dataset.",
        )
