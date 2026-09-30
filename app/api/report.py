"""API endpoints for Combined DataGuard Quality Reports, Persistence, and Retrieval."""

import io
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
import pandas as pd
from sqlalchemy.orm import Session

from app.core.health_score import HealthScoreCalculator
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.dataset import Dataset
from app.models.report import Report
from app.schemas.db import ReportListItem
from app.schemas.health import DataGuardReport

logger = get_logger(__name__)

router = APIRouter(tags=["Reports & Persistence"])


@router.post(
    "/report",
    response_model=DataGuardReport,
    summary="Generate & Store Comprehensive DataGuard Quality Report",
    description=(
        "Upload a CSV dataset to execute the full DataGuard pipeline: statistical profiling, "
        "data quality validation, Isolation Forest anomaly detection, health scoring, "
        "and persist the resulting report in PostgreSQL."
    ),
    status_code=status.HTTP_200_OK,
)
async def generate_and_save_report(
    file: UploadFile = File(..., description="CSV file to analyze"),
    db: Session = Depends(get_db),
) -> DataGuardReport:
    """Run full DataGuard analysis, calculate health score, and persist results to PostgreSQL."""
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

    # 4. Run Combined Pipeline
    try:
        calculator = HealthScoreCalculator()
        report = calculator.generate_report(df, include_details=True)
    except Exception as err:
        logger.error("Error generating report: %s", err, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the DataGuard report.",
        )

    # 5. Persist Dataset and Report to Database
    try:
        dataset_record = Dataset(
            filename=file.filename or "dataset.csv",
            row_count=report.summary.rows,
            column_count=report.summary.columns,
            health_score=report.health_score,
            health_status=report.status.value,
        )
        db.add(dataset_record)
        db.flush()

        report_dict = report.model_dump(mode="json")
        report_record = Report(
            dataset_id=dataset_record.id,
            missing_values=report.summary.missing_values,
            duplicate_rows=report.summary.duplicates,
            validation_violations=report.summary.validation_violations,
            anomalies=report.summary.anomalies,
            health_score=report.health_score,
            health_status=report.status.value,
            report_data=report_dict,
        )
        db.add(report_record)
        db.commit()
        db.refresh(report_record)

        report.id = report_record.id
        report.dataset_id = dataset_record.id
        report.filename = dataset_record.filename
        report.created_at = report_record.created_at

        logger.info(
            "Report #%d saved to database for dataset '%s' (Health Score: %.2f)",
            report_record.id,
            dataset_record.filename,
            report.health_score,
        )
        return report

    except Exception as db_err:
        db.rollback()
        logger.error("Database persistence error: %s", db_err, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the report to the database.",
        )


@router.get(
    "/reports",
    response_model=List[ReportListItem],
    summary="List Stored Reports",
    description="Retrieve a list of summary records for all previously analyzed and stored reports in PostgreSQL.",
    status_code=status.HTTP_200_OK,
)
def list_reports(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> List[ReportListItem]:
    """Retrieve summary metadata for all saved reports in reverse chronological order."""
    try:
        results = (
            db.query(Report, Dataset)
            .join(Dataset, Report.dataset_id == Dataset.id)
            .order_by(Report.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        items: List[ReportListItem] = []
        for rep, dset in results:
            items.append(
                ReportListItem(
                    id=rep.id,
                    dataset_id=rep.dataset_id,
                    filename=dset.filename,
                    row_count=dset.row_count,
                    column_count=dset.column_count,
                    missing_values=rep.missing_values,
                    duplicate_rows=rep.duplicate_rows,
                    validation_violations=rep.validation_violations,
                    anomalies=rep.anomalies,
                    health_score=rep.health_score,
                    health_status=rep.health_status,
                    created_at=rep.created_at,
                )
            )
        return items
    except Exception as err:
        logger.error("Database error while listing reports: %s", err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reports from the database.",
        )


@router.get(
    "/reports/{report_id}",
    response_model=DataGuardReport,
    summary="Get Stored Report by ID",
    description="Retrieve the complete analysis details and scores of a previously saved report by its report ID.",
    status_code=status.HTTP_200_OK,
)
def get_report_by_id(
    report_id: int,
    db: Session = Depends(get_db),
) -> DataGuardReport:
    """Retrieve a full previously saved DataGuard report by ID."""
    try:
        report_record = db.query(Report).filter(Report.id == report_id).first()
        if not report_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID {report_id} not found.",
            )

        data = dict(report_record.report_data)
        data["id"] = report_record.id
        data["dataset_id"] = report_record.dataset_id
        data["created_at"] = report_record.created_at
        if report_record.dataset:
            data["filename"] = report_record.dataset.filename

        return DataGuardReport.model_validate(data)
    except HTTPException:
        raise
    except Exception as err:
        logger.error("Database error retrieving report #%d: %s", report_id, err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report #{report_id} from database.",
        )
