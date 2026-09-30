"""Unit and integration tests for PostgreSQL persistence and database models."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.dataset import Dataset
from app.models.report import Report
from app.schemas.health import HealthStatus
from tests.conftest import TestingSessionLocal

client = TestClient(app)


# =====================================================================
# 1. UNIT TESTS FOR DATABASE MODELS
# =====================================================================


def test_dataset_and_report_model_creation() -> None:
    """Verify that Dataset and Report models can be created and linked via relationship."""
    db = TestingSessionLocal()

    dataset = Dataset(
        filename="test_transactions.csv",
        row_count=100,
        column_count=5,
        health_score=92.5,
        health_status="EXCELLENT",
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    assert dataset.id is not None
    assert dataset.filename == "test_transactions.csv"
    assert dataset.health_score == 92.5

    report_payload = {
        "health_score": 92.5,
        "status": "EXCELLENT",
        "summary": {
            "rows": 100,
            "columns": 5,
            "missing_values": 0,
            "duplicates": 0,
            "validation_violations": 0,
            "anomalies": 2,
        },
        "score_breakdown": {
            "completeness_score": 100.0,
            "validation_score": 100.0,
            "uniqueness_score": 100.0,
            "anomaly_score": 98.0,
        },
        "recommendations": ["Dataset quality is excellent."],
    }

    report = Report(
        dataset_id=dataset.id,
        missing_values=0,
        duplicate_rows=0,
        validation_violations=0,
        anomalies=2,
        health_score=92.5,
        health_status="EXCELLENT",
        report_data=report_payload,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    assert report.id is not None
    assert report.dataset_id == dataset.id
    assert report.dataset.filename == "test_transactions.csv"
    assert len(dataset.reports) == 1

    db.close()


# =====================================================================
# 2. API INTEGRATION TESTS (POST /report, GET /reports, GET /reports/{id})
# =====================================================================


def test_api_post_report_persists_to_database() -> None:
    """Test that POST /report computes analysis and persists Dataset & Report in database."""
    with open("data/sample_transactions.csv", "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/report",
        files={"file": ("sample_transactions.csv", file_bytes, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()

    assert "id" in data and data["id"] is not None
    assert "dataset_id" in data and data["dataset_id"] is not None
    assert data["filename"] == "sample_transactions.csv"
    assert data["health_score"] > 0.0


def test_api_list_reports() -> None:
    """Test GET /reports returns list of previously persisted reports."""
    clean_csv = (
        "transaction_id,customer_id,transaction_date,amount,payment_method\n"
        "TXN-1,CUST-1,2026-03-01 10:00:00,50.0,UPI\n"
        "TXN-2,CUST-2,2026-03-01 11:00:00,150.0,Credit Card\n"
    )

    client.post(
        "/report",
        files={"file": ("batch_1.csv", clean_csv.encode("utf-8"), "text/csv")},
    )
    client.post(
        "/report",
        files={"file": ("batch_2.csv", clean_csv.encode("utf-8"), "text/csv")},
    )

    response = client.get("/reports")
    assert response.status_code == 200
    reports = response.json()

    assert len(reports) == 2
    assert reports[0]["filename"] in ["batch_1.csv", "batch_2.csv"]
    assert reports[0]["health_score"] >= 90.0
    assert "id" in reports[0]
    assert "dataset_id" in reports[0]


def test_api_get_report_by_id_success() -> None:
    """Test GET /reports/{report_id} retrieves a specific saved report."""
    clean_csv = (
        "transaction_id,customer_id,transaction_date,amount,payment_method\n"
        "TXN-1,CUST-1,2026-03-01 10:00:00,50.0,UPI\n"
    )

    post_resp = client.post(
        "/report",
        files={"file": ("target.csv", clean_csv.encode("utf-8"), "text/csv")},
    )
    assert post_resp.status_code == 200
    report_id = post_resp.json()["id"]

    get_resp = client.get(f"/reports/{report_id}")
    assert get_resp.status_code == 200
    report_data = get_resp.json()

    assert report_data["id"] == report_id
    assert report_data["filename"] == "target.csv"
    assert report_data["status"] == "EXCELLENT"
    assert "summary" in report_data
    assert "score_breakdown" in report_data


def test_api_get_report_by_id_not_found() -> None:
    """Test GET /reports/999999 returns 404 Not Found."""
    response = client.get("/reports/999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
