"""Unit and integration tests for AnomalyDetector and POST /anomalies endpoint."""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.anomaly_detector import AnomalyDetector
from app.main import app
from app.schemas.anomaly import AnomalyStatus

client = TestClient(app)


# =====================================================================
# 1. UNIT TESTS FOR ANOMALY DETECTOR
# =====================================================================


def test_anomaly_detector_runs_on_valid_data() -> None:
    """Verify that Isolation Forest runs smoothly on clean numeric data."""
    # Generate 50 standard records
    np.random.seed(42)
    amounts = np.random.normal(loc=100.0, scale=10.0, size=50).tolist()
    df = pd.DataFrame({"transaction_id": [f"TXN-{i}" for i in range(50)], "amount": amounts})

    detector = AnomalyDetector(contamination=0.05, random_state=42)
    report = detector.detect_anomalies(df)

    assert report.total_records == 50
    assert "amount" in report.features_used
    assert isinstance(report.anomaly_count, int)
    assert report.anomaly_count >= 0
    assert report.anomaly_percentage >= 0.0


def test_anomaly_detector_identifies_extreme_outliers() -> None:
    """Verify that obvious numeric anomalies are detected."""
    # 48 normal transactions between 50 and 150, 2 extreme outliers at 50,000 and 100,000
    normal_amounts = [50.0 + i for i in range(48)]
    anomalous_amounts = [50000.0, 100000.0]
    all_amounts = normal_amounts + anomalous_amounts

    df = pd.DataFrame({
        "transaction_id": [f"TXN-{i}" for i in range(50)],
        "amount": all_amounts,
    })

    detector = AnomalyDetector(contamination=0.04, random_state=42)
    report = detector.detect_anomalies(df)

    assert report.total_records == 50
    assert report.anomaly_count > 0

    # Ensure the extreme records (row 48 and 49) are in the anomalies list
    anomalous_indices = [a.row_index for a in report.anomalies]
    assert 48 in anomalous_indices or 49 in anomalous_indices
    for a in report.anomalies:
        assert a.status == AnomalyStatus.ANOMALY
        assert a.is_anomaly is True


def test_anomaly_detector_handles_missing_values() -> None:
    """Verify that missing/NaN values in numeric features do not crash the detector."""
    amounts = [100.0, np.nan, 105.0, None, 110.0, 95.0, 102.0, 50000.0]
    df = pd.DataFrame({
        "transaction_id": [f"TXN-{i}" for i in range(len(amounts))],
        "amount": amounts,
    })

    detector = AnomalyDetector(contamination=0.15, random_state=42)
    report = detector.detect_anomalies(df)

    assert report.total_records == 8
    assert "amount" in report.features_used
    assert report.anomaly_count > 0


def test_anomaly_detector_no_numeric_features() -> None:
    """Verify safe handling when dataset contains no numeric features."""
    df = pd.DataFrame({
        "customer_name": ["Alice", "Bob", "Charlie"],
        "city": ["New York", "London", "Paris"],
    })

    detector = AnomalyDetector()
    report = detector.detect_anomalies(df)

    assert report.total_records == 3
    assert report.anomaly_count == 0
    assert report.anomaly_percentage == 0.0
    assert report.features_used == []
    assert report.anomalies == []


def test_anomaly_detector_empty_dataframe() -> None:
    """Verify safe handling when dataset is completely empty."""
    df = pd.DataFrame()
    detector = AnomalyDetector()
    report = detector.detect_anomalies(df)

    assert report.total_records == 0
    assert report.anomaly_count == 0
    assert report.anomaly_percentage == 0.0
    assert report.anomalies == []


def test_anomaly_detector_single_row() -> None:
    """Verify handling when dataset has fewer than 2 rows."""
    df = pd.DataFrame({"amount": [150.0]})
    detector = AnomalyDetector()
    report = detector.detect_anomalies(df)

    assert report.total_records == 1
    assert report.anomaly_count == 0
    assert report.anomalies == []


def test_anomaly_detector_does_not_modify_dataframe() -> None:
    """Verify that anomaly detection does not mutate the input DataFrame."""
    df = pd.DataFrame({
        "transaction_id": ["TXN-1", "TXN-2", "TXN-3", "TXN-4"],
        "amount": [100.0, 200.0, 300.0, 400.0],
    })
    df_copy = df.copy(deep=True)

    detector = AnomalyDetector()
    _ = detector.detect_anomalies(df)

    pd.testing.assert_frame_equal(df, df_copy)


# =====================================================================
# 2. API INTEGRATION TESTS FOR POST /anomalies
# =====================================================================


def test_api_anomalies_sample_csv_success() -> None:
    """Test detecting anomalies on sample_transactions.csv via POST /anomalies."""
    with open("data/sample_transactions.csv", "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/anomalies",
        files={"file": ("sample_transactions.csv", file_bytes, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] == 150
    assert data["anomaly_count"] > 0
    assert data["anomaly_percentage"] > 0.0
    assert "amount" in data["features_used"]
    assert len(data["anomalies"]) == data["anomaly_count"]

    # Verify anomalous record structure
    first_anomaly = data["anomalies"][0]
    assert "row_index" in first_anomaly
    assert "anomaly_score" in first_anomaly
    assert first_anomaly["status"] == "ANOMALY"
    assert first_anomaly["is_anomaly"] is True
    assert "amount" in first_anomaly["features"]


def test_api_anomalies_invalid_extension() -> None:
    """Test that uploading a non-CSV file returns 400 Bad Request."""
    response = client.post(
        "/anomalies",
        files={"file": ("report.txt", b"some text data", "text/plain")},
    )
    assert response.status_code == 400
    assert "Uploaded file must have a .csv extension" in response.json()["detail"]


def test_api_anomalies_empty_file() -> None:
    """Test that uploading an empty CSV returns 400 Bad Request."""
    response = client.post(
        "/anomalies",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 400
    assert "The uploaded CSV file is empty" in response.json()["detail"]
