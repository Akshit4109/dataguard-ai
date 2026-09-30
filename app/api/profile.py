"""API endpoints for Data Profiling."""

import io
from fastapi import APIRouter, File, HTTPException, UploadFile, status
import pandas as pd

from app.core.logging import get_logger
from app.core.profiler import DataProfiler
from app.schemas.profiling import DatasetProfile

logger = get_logger(__name__)

router = APIRouter(tags=["Profiling"])


@router.post(
    "/profile",
    response_model=DatasetProfile,
    summary="Profile a CSV Dataset",
    description=(
        "Upload a CSV file to automatically analyze its structure, completeness, "
        "data types, uniqueness, duplicates, and column-level summary statistics."
    ),
    status_code=status.HTTP_200_OK,
)
async def profile_dataset(
    file: UploadFile = File(..., description="CSV file to profile"),
) -> DatasetProfile:
    """Analyze and generate a comprehensive profile for an uploaded CSV file."""
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

    # 4. Generate profile
    try:
        profiler = DataProfiler()
        profile_result = profiler.profile(df)
        logger.info(
            "Successfully profiled dataset '%s' (%d rows, %d columns)",
            file.filename,
            profile_result.row_count,
            profile_result.column_count,
        )
        return profile_result
    except Exception as err:
        logger.error("Profiling execution error: %s", err, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the dataset profile.",
        )
