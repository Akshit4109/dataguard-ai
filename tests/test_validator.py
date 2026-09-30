"""Unit and integration tests for DataValidator and POST /validate endpoint."""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.validator import DataValidator, get_default_transaction_rules
from app.main import app
from app.schemas.validation import (
    ColumnRule,
    SeverityLevel,
    ValidationConfig,
    ValidationRuleType,
)

client = TestClient(app)


# =====================================================================
# 1. UNIT TESTS FOR DATAVALIDATOR
# =====================================================================


def test_missing_required_values() -> None:
    """Verify that required/non-null rule detects missing values and reports violations."""
    df = pd.DataFrame({
        "customer_id": ["CUST-1", None, "CUST-3", None],
    })
    config = ValidationConfig(
        column_rules=[
            ColumnRule(column="customer_id", required=True),
        ]
    )
    validator = DataValidator()
    report = validator.validate(df, config=config)

    assert report.total_rules == 1
    assert report.failed_rules == 1
    assert not report.is_valid

    res = report.results[0]
    assert res.rule == ValidationRuleType.REQUIRED.value
    assert res.column == "customer_id"
    assert not res.passed
    assert res.violations == 2
    assert "2 record(s) contain missing/null values" in res.message


def test_duplicate_unique_values() -> None:
    """Verify that uniqueness rule detects duplicate records."""
    df = pd.DataFrame({
        "transaction_id": ["TXN-1", "TXN-2", "TXN-1", "TXN-3", "TXN-2"],
    })
    config = ValidationConfig(
        column_rules=[
            ColumnRule(column="transaction_id", unique=True),
        ]
    )
    validator = DataValidator()
    report = validator.validate(df, config=config)

    assert report.total_rules == 1
    assert report.failed_rules == 1
    assert not report.is_valid

    res = report.results[0]
    assert res.rule == ValidationRuleType.UNIQUE.value
    assert res.column == "transaction_id"
    assert not res.passed
    assert res.violations == 2
    assert "2 duplicate record(s) found" in res.message


def test_negative_numeric_amounts() -> None:
    """Verify that numeric range rule detects values below minimum constraint."""
    df = pd.DataFrame({
        "amount": [100.5, -20.0, 50.0, -5.0, 0.0],
    })
    config = ValidationConfig(
        column_rules=[
            ColumnRule(column="amount", min_value=0.0),
        ]
    )
    validator = DataValidator()
    report = validator.validate(df, config=config)

    assert report.total_rules == 1
    assert report.failed_rules == 1
    assert not report.is_valid

    res = report.results[0]
    assert res.rule == ValidationRuleType.NUMERIC_RANGE.value
    assert res.column == "amount"
    assert not res.passed
    assert res.violations == 2
    assert "2 record(s) in 'amount' violate range constraint (>= 0.0)" in res.message


def test_invalid_categorical_allowed_values() -> None:
    """Verify that allowed values rule detects categorical values not in permitted list."""
    df = pd.DataFrame({
        "payment_method": ["UPI", "Bitcoin", "Credit Card", "Gold", "Debit Card"],
    })
    config = ValidationConfig(
        column_rules=[
            ColumnRule(
                column="payment_method",
                allowed_values=["UPI", "Credit Card", "Debit Card", "Net Banking", "Wallet"],
            ),
        ]
    )
    validator = DataValidator()
    report = validator.validate(df, config=config)

    assert report.total_rules == 1
    assert report.failed_rules == 1
    assert not report.is_valid

    res = report.results[0]
    assert res.rule == ValidationRuleType.ALLOWED_VALUES.value
    assert res.column == "payment_method"
    assert not res.passed
    assert res.violations == 2
    assert "2 record(s) in 'payment_method' contain values not in allowed set" in res.message


def test_missing_required_columns_schema_check() -> None:
    """Verify schema check detects missing columns."""
    df = pd.DataFrame({
        "transaction_id": ["TXN-1", "TXN-2"],
        "customer_id": ["CUST-1", "CUST-2"],
    })
    config = ValidationConfig(
        required_columns=["transaction_id", "customer_id", "amount", "payment_method"],
    )
    validator = DataValidator()
    report = validator.validate(df, config=config)

    assert report.total_rules == 4
    assert report.passed_rules == 2
    assert report.failed_rules == 2
    assert not report.is_valid

    failed = [r for r in report.results if not r.passed]
    failed_col_names = [f.column for f in failed]
    assert "amount" in failed_col_names
    assert "payment_method" in failed_col_names


def test_completely_valid_dataset() -> None:
    """Verify that completely clean data passes all validation rules with zero violations."""
    df = pd.DataFrame({
        "transaction_id": ["TXN-101", "TXN-102", "TXN-103"],
        "customer_id": ["CUST-1", "CUST-2", "CUST-3"],
        "transaction_date": ["2026-03-01", "2026-03-02", "2026-03-03"],
        "amount": [150.0, 25.5, 99.99],
        "payment_method": ["UPI", "Credit Card", "Debit Card"],
    })
    validator = DataValidator()
    report = validator.validate(df)  # Uses default transaction rules

    assert report.is_valid
    assert report.failed_rules == 0
    assert report.passed_rules == report.total_rules
    for r in report.results:
        assert r.passed
        assert r.violations == 0


def test_validator_does_not_modify_dataframe() -> None:
    """Verify that validation does not mutate the input DataFrame."""
    original_data = {
        "transaction_id": ["TXN-1", "TXN-2"],
        "amount": [10.5, 20.5],
    }
    df = pd.DataFrame(original_data)
    df_copy = df.copy(deep=True)

    validator = DataValidator()
    _ = validator.validate(df)

    pd.testing.assert_frame_equal(df, df_copy)


# =====================================================================
# 2. API INTEGRATION TESTS FOR POST /validate
# =====================================================================


def test_api_validate_sample_csv_success() -> None:
    """Test validating sample_transactions.csv via POST /validate."""
    with open("data/sample_transactions.csv", "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/validate",
        files={"file": ("sample_transactions.csv", file_bytes, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()

    # sample_transactions.csv has 2 duplicate rows and 5 missing values (amount, payment_method, city)
    assert not data["is_valid"]
    assert data["failed_rules"] > 0
    assert data["total_rules"] == len(data["results"])

    # Check for specific violations we expect from the sample dataset
    rule_map = {(r["rule"], r["column"]): r for r in data["results"]}
    
    # transaction_id uniqueness should fail due to 2 duplicate rows
    assert ("unique", "transaction_id") in rule_map
    assert not rule_map[("unique", "transaction_id")]["passed"]
    assert rule_map[("unique", "transaction_id")]["violations"] == 2

    # amount required should fail due to 2 missing values
    assert ("required", "amount") in rule_map
    assert not rule_map[("required", "amount")]["passed"]
    assert rule_map[("required", "amount")]["violations"] == 2


def test_api_validate_clean_csv_success() -> None:
    """Test validating a perfectly clean CSV returns is_valid=True."""
    clean_csv = (
        "transaction_id,customer_id,transaction_date,amount,payment_method\n"
        "TXN-1,CUST-1,2026-03-01 10:00:00,50.0,UPI\n"
        "TXN-2,CUST-2,2026-03-01 11:00:00,150.0,Credit Card\n"
    )
    response = client.post(
        "/validate",
        files={"file": ("clean.csv", clean_csv.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["failed_rules"] == 0


def test_api_validate_invalid_extension() -> None:
    """Test that uploading a non-CSV file returns 400 Bad Request."""
    response = client.post(
        "/validate",
        files={"file": ("data.json", b'{"key": "value"}', "application/json")},
    )
    assert response.status_code == 400
    assert "Uploaded file must have a .csv extension" in response.json()["detail"]


def test_api_validate_empty_file() -> None:
    """Test that uploading an empty CSV file returns 400 Bad Request."""
    response = client.post(
        "/validate",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 400
    assert "The uploaded CSV file is empty" in response.json()["detail"]
