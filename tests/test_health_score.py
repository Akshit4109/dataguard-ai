"""Unit and integration tests for HealthScoreCalculator and POST /report endpoint."""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.health_score import HealthScoreCalculator
from app.main import app
from app.schemas.health import HealthStatus

client = TestClient(app)


# =====================================================================
# 1. UNIT TESTS FOR HEALTH SCORE CALCULATOR
# =====================================================================


def test_clean_dataset_receives_high_score() -> None:
    """Verify that a clean dataset receives an EXCELLENT health score (>= 90)."""
    # 20 rows of identical clean transactions with no nulls, unique IDs, uniform amounts
    data = {
        "transaction_id": [f"TXN-{1000 + i}" for i in range(20)],
        "customer_id": [f"CUST-{2000 + i}" for i in range(20)],
        "transaction_date": [f"2026-03-01 10:{i:02d}:00" for i in range(20)],
        "amount": [100.0] * 20,
        "payment_method": ["UPI"] * 20,
    }
    df = pd.DataFrame(data)

    calculator = HealthScoreCalculator()
    report = calculator.generate_report(df)

    assert 90.0 <= report.health_score <= 100.0
    assert report.status == HealthStatus.EXCELLENT
    assert report.summary.missing_values == 0
    assert report.summary.duplicates == 0
    assert report.summary.validation_violations == 0
    assert len(report.recommendations) > 0
    assert "excellent" in report.recommendations[0].lower()


def test_poor_quality_dataset_receives_low_score() -> None:
    """Verify that a dataset with heavy missing values, duplicates, and rule violations receives a low score."""
    # Create dataset with duplicate rows, heavy missing values, and invalid payment methods
    bad_row = {
        "transaction_id": "TXN-1",
        "customer_id": None,
        "transaction_date": None,
        "amount": -500.0,
        "payment_method": "InvalidCrypto",
    }
    # 5 identical bad rows -> 4 duplicates, 10 missing values, negative amounts, invalid categories
    df = pd.DataFrame([bad_row] * 5)

    calculator = HealthScoreCalculator()
    report = calculator.generate_report(df)

    assert report.health_score < 75.0
    assert report.status in (HealthStatus.POOR, HealthStatus.NEEDS_ATTENTION)
    assert report.summary.missing_values > 0
    assert report.summary.duplicates > 0
    assert report.summary.validation_violations > 0


def test_health_score_stays_bounded_between_0_and_100() -> None:
    """Verify that health scores never exceed 100.0 or drop below 0.0 under extreme conditions."""
    calculator = HealthScoreCalculator()

    # Worst-case scenario dataset
    worst_df = pd.DataFrame({
        "transaction_id": ["TXN-DUP"] * 20,
        "customer_id": [None] * 20,
        "transaction_date": [None] * 20,
        "amount": [-1000.0] * 20,
        "payment_method": ["IllegalToken"] * 20,
    })
    worst_report = calculator.generate_report(worst_df)
    assert 0.0 <= worst_report.health_score <= 100.0

    # Best-case scenario dataset
    best_df = pd.DataFrame({
        "transaction_id": [f"TXN-{i}" for i in range(30)],
        "customer_id": [f"CUST-{i}" for i in range(30)],
        "transaction_date": ["2026-03-01 10:00:00"] * 30,
        "amount": [50.0] * 30,
        "payment_method": ["UPI"] * 30,
    })
    best_report = calculator.generate_report(best_df)
    assert 0.0 <= best_report.health_score <= 100.0


def test_status_classification_thresholds() -> None:
    """Verify that health score correctly maps to classification status enum."""
    calculator = HealthScoreCalculator()

    clean_df = pd.DataFrame({
        "transaction_id": [f"TXN-{i}" for i in range(20)],
        "customer_id": [f"CUST-{i}" for i in range(20)],
        "transaction_date": ["2026-03-01 10:00:00"] * 20,
        "amount": [50.0] * 20,
        "payment_method": ["UPI"] * 20,
    })
    rep = calculator.generate_report(clean_df)
    if rep.health_score >= 90.0:
        assert rep.status == HealthStatus.EXCELLENT
    elif rep.health_score >= 75.0:
        assert rep.status == HealthStatus.GOOD


def test_rule_based_recommendations_generation() -> None:
    """Verify that appropriate rule-based recommendations are generated when issues exist."""
    row1 = {
        "transaction_id": "TXN-1",
        "customer_id": None,
        "transaction_date": "2026-03-01",
        "amount": -10.0,
        "payment_method": "Bitcoin",
    }
    row2 = {
        "transaction_id": "TXN-2",
        "customer_id": "CUST-2",
        "transaction_date": "2026-03-02",
        "amount": 50000.0,
        "payment_method": "UPI",
    }
    # Duplicate row1 to trigger duplicate row recommendation
    df = pd.DataFrame([row1, row1, row2])

    calculator = HealthScoreCalculator()
    report = calculator.generate_report(df)

    rec_text = " ".join(report.recommendations).lower()
    assert "missing" in rec_text
    assert "duplicate" in rec_text
    assert "validation" in rec_text


# =====================================================================
# 2. API INTEGRATION TESTS FOR POST /report
# =====================================================================


def test_api_report_sample_csv_success() -> None:
    """Test generating a combined report on sample_transactions.csv via POST /report."""
    with open("data/sample_transactions.csv", "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/report",
        files={"file": ("sample_transactions.csv", file_bytes, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()

    # Check top-level report structure
    assert "health_score" in data
    assert 0.0 <= data["health_score"] <= 100.0
    assert data["status"] in ["EXCELLENT", "GOOD", "NEEDS_ATTENTION", "POOR"]
    assert "summary" in data
    assert data["summary"]["rows"] == 150
    assert data["summary"]["columns"] == 8
    assert data["summary"]["missing_values"] == 5
    assert data["summary"]["duplicates"] == 2

    # Check score breakdown
    assert "score_breakdown" in data
    assert "completeness_score" in data["score_breakdown"]
    assert "validation_score" in data["score_breakdown"]
    assert "uniqueness_score" in data["score_breakdown"]
    assert "anomaly_score" in data["score_breakdown"]

    # Check recommendations
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0

    # Check embedded detailed sub-reports
    assert "profile" in data and data["profile"] is not None
    assert "validation" in data and data["validation"] is not None
    assert "anomalies" in data and data["anomalies"] is not None


def test_api_report_clean_csv_success() -> None:
    """Test generating a combined report on a completely clean CSV returns EXCELLENT status."""
    clean_csv = (
        "transaction_id,customer_id,transaction_date,amount,payment_method\n"
        "TXN-1,CUST-1,2026-03-01 10:00:00,50.0,UPI\n"
        "TXN-2,CUST-2,2026-03-01 11:00:00,50.0,Credit Card\n"
        "TXN-3,CUST-3,2026-03-01 12:00:00,50.0,Debit Card\n"
    )
    response = client.post(
        "/report",
        files={"file": ("clean.csv", clean_csv.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["health_score"] >= 90.0
    assert data["status"] == "EXCELLENT"


def test_api_report_invalid_file_extension() -> None:
    """Test that uploading a non-CSV file returns 400 Bad Request."""
    response = client.post(
        "/report",
        files={"file": ("data.xml", b"<root></root>", "application/xml")},
    )
    assert response.status_code == 400
    assert "Uploaded file must have a .csv extension" in response.json()["detail"]


def test_api_report_empty_file() -> None:
    """Test that uploading an empty CSV returns 400 Bad Request."""
    response = client.post(
        "/report",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 400
    assert "The uploaded CSV file is empty" in response.json()["detail"]
