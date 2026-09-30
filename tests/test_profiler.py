"""Unit and integration tests for DataProfiler and POST /profile endpoint."""

import io
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.profiler import DataProfiler
from app.main import app
from app.schemas.profiling import LogicalType

client = TestClient(app)


# =====================================================================
# 1. UNIT TESTS FOR DATAPROFILER
# =====================================================================


def test_row_and_column_counting() -> None:
    """Verify that row_count, column_count, and total_cells are calculated correctly."""
    df = pd.DataFrame({
        "a": [1, 2, 3, 4],
        "b": ["x", "y", "z", "w"],
        "c": [10.5, 20.5, 30.5, 40.5],
    })
    profiler = DataProfiler()
    profile = profiler.profile(df)

    assert profile.row_count == 4
    assert profile.column_count == 3
    assert profile.total_cells == 12
    assert len(profile.columns) == 3


def test_missing_values_analysis() -> None:
    """Verify missing values count and percentage calculation at dataset and column levels."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "score": [10.0, None, np.nan, 40.0],  # 2 missing
        "label": ["A", "B", None, "D"],       # 1 missing
    })
    profiler = DataProfiler()
    profile = profiler.profile(df)

    assert profile.total_missing_values == 3
    assert profile.total_cells == 12
    assert profile.missing_percentage == round((3 / 12) * 100, 2)

    col_map = {c.name: c for c in profile.columns}
    assert col_map["score"].missing_count == 2
    assert col_map["score"].missing_percentage == 50.0
    assert col_map["score"].non_null_count == 2

    assert col_map["label"].missing_count == 1
    assert col_map["label"].missing_percentage == 25.0
    assert col_map["label"].non_null_count == 3


def test_duplicate_detection() -> None:
    """Verify duplicate row detection and percentage calculation."""
    df = pd.DataFrame({
        "col1": [1, 2, 2, 1],
        "col2": ["a", "b", "b", "a"],
    })  # 4 rows, 2 are duplicate copies of previous rows
    profiler = DataProfiler()
    profile = profiler.profile(df)

    assert profile.duplicate_rows == 2
    assert profile.duplicate_percentage == 50.0


def test_numeric_statistics() -> None:
    """Verify statistical metric computations for numeric columns."""
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    df = pd.DataFrame({"metric": values})

    profiler = DataProfiler()
    profile = profiler.profile(df)

    col = profile.columns[0]
    assert col.logical_type == LogicalType.NUMERIC.value
    assert col.numeric_stats is not None
    assert col.numeric_stats.min == 10.0
    assert col.numeric_stats.max == 50.0
    assert col.numeric_stats.mean == 30.0
    assert col.numeric_stats.median == 30.0
    assert col.numeric_stats.std is not None and round(col.numeric_stats.std, 2) == 15.81
    assert col.numeric_stats.percentile_25 == 20.0
    assert col.numeric_stats.percentile_50 == 30.0
    assert col.numeric_stats.percentile_75 == 40.0


def test_categorical_statistics() -> None:
    """Verify categorical frequency and mode detection."""
    df = pd.DataFrame({"city": ["London", "Paris", "London", "Tokyo", "London", "Paris"]})

    profiler = DataProfiler()
    profile = profiler.profile(df)

    col = profile.columns[0]
    assert col.logical_type == LogicalType.CATEGORICAL.value
    assert col.categorical_stats is not None
    assert col.categorical_stats.most_frequent_value == "London"
    assert col.categorical_stats.most_frequent_count == 3
    assert col.categorical_stats.unique_count == 3
    assert col.numeric_stats is None


def test_unique_counts_and_percentages() -> None:
    """Verify unique counts and percentages."""
    df = pd.DataFrame({
        "category": ["A", "B", "A", "C", "A"],
    })
    profiler = DataProfiler()
    profile = profiler.profile(df)

    col = profile.columns[0]
    assert col.unique_count == 3
    assert col.unique_percentage == 60.0  # 3/5 * 100


def test_boolean_column_detection() -> None:
    """Verify boolean dtype detection and statistics."""
    df = pd.DataFrame({
        "is_active": [True, False, True, True, False],
    })
    profiler = DataProfiler()
    profile = profiler.profile(df)

    assert profile.boolean_columns == 1
    assert profile.numeric_columns == 0
    col = profile.columns[0]
    assert col.logical_type == LogicalType.BOOLEAN.value
    assert col.categorical_stats is not None
    assert col.categorical_stats.most_frequent_value is True
    assert col.categorical_stats.most_frequent_count == 3
    assert col.categorical_stats.unique_count == 2


def test_datetime_column_detection() -> None:
    """Verify datetime dtype detection and min/max date calculation."""
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-01-01 10:00:00", "2026-01-05 15:30:00", "2026-01-03 08:00:00"]),
    })
    profiler = DataProfiler()
    profile = profiler.profile(df)

    assert profile.datetime_columns == 1
    col = profile.columns[0]
    assert col.logical_type == LogicalType.DATETIME.value
    assert col.datetime_stats is not None
    assert "2026-01-01" in str(col.datetime_stats.min_date)
    assert "2026-01-05" in str(col.datetime_stats.max_date)


def test_empty_dataframe() -> None:
    """Verify safe handling of an empty DataFrame."""
    # Empty with columns
    df = pd.DataFrame(columns=["col1", "col2", "col3"])
    profiler = DataProfiler()
    profile = profiler.profile(df)

    assert profile.row_count == 0
    assert profile.column_count == 3
    assert profile.total_cells == 0
    assert profile.duplicate_rows == 0
    assert profile.duplicate_percentage == 0.0
    assert profile.total_missing_values == 0
    assert profile.missing_percentage == 0.0

    # Completely empty (0 rows, 0 columns)
    empty_df = pd.DataFrame()
    empty_profile = profiler.profile(empty_df)
    assert empty_profile.row_count == 0
    assert empty_profile.column_count == 0
    assert empty_profile.total_cells == 0


def test_mixed_and_unusual_types() -> None:
    """Verify that mixed object columns and all-null columns do not crash the profiler."""
    df = pd.DataFrame({
        "mixed": [1, "two", 3.0, None, object()],
        "all_null": [None, np.nan, None, None, None],
        "single_row_numeric": [42.0, np.nan, np.nan, np.nan, np.nan],
    })
    profiler = DataProfiler()
    profile = profiler.profile(df)

    assert profile.row_count == 5
    assert profile.column_count == 3
    col_map = {c.name: c for c in profile.columns}

    assert col_map["all_null"].missing_count == 5
    assert col_map["all_null"].non_null_count == 0
    assert col_map["single_row_numeric"].numeric_stats is not None
    assert col_map["single_row_numeric"].numeric_stats.min == 42.0
    assert col_map["single_row_numeric"].numeric_stats.std == 0.0


def test_input_dataframe_not_modified() -> None:
    """Verify that profiling does not mutate or alter the original DataFrame in any way."""
    original_data = {
        "val": [10, 20, 30],
        "cat": ["A", "B", "C"],
    }
    df = pd.DataFrame(original_data)
    df_copy = df.copy(deep=True)

    profiler = DataProfiler()
    _ = profiler.profile(df)

    pd.testing.assert_frame_equal(df, df_copy)


# =====================================================================
# 2. API INTEGRATION TESTS FOR POST /profile
# =====================================================================


def test_api_profile_sample_csv_success() -> None:
    """Test successful profiling of sample_transactions.csv via POST /profile."""
    with open("data/sample_transactions.csv", "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/profile",
        files={"file": ("sample_transactions.csv", file_bytes, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["row_count"] == 150
    assert data["column_count"] == 8
    assert data["total_cells"] == 1200
    assert data["duplicate_rows"] == 2
    assert data["duplicate_percentage"] == round((2 / 150) * 100, 2)
    assert data["total_missing_values"] == 5
    assert len(data["columns"]) == 8

    # Verify column presence
    col_names = [c["name"] for c in data["columns"]]
    expected_cols = [
        "transaction_id",
        "customer_id",
        "transaction_date",
        "amount",
        "payment_method",
        "merchant_category",
        "city",
        "transaction_status",
    ]
    for expected in expected_cols:
        assert expected in col_names


def test_api_profile_invalid_file_extension() -> None:
    """Test that uploading a non-CSV file returns a 400 Bad Request."""
    response = client.post(
        "/profile",
        files={"file": ("document.pdf", b"fake pdf content", "application/pdf")},
    )
    assert response.status_code == 400
    assert "Uploaded file must have a .csv extension" in response.json()["detail"]


def test_api_profile_empty_csv() -> None:
    """Test that uploading an empty CSV file returns a 400 Bad Request."""
    response = client.post(
        "/profile",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 400
    assert "The uploaded CSV file is empty" in response.json()["detail"]


def test_api_profile_malformed_csv() -> None:
    """Test handling of a malformed or corrupted CSV."""
    response = client.post(
        "/profile",
        files={"file": ("bad.csv", b"\x00\x01\x02\xff\xfe", "text/csv")},
    )
    assert response.status_code == 400
