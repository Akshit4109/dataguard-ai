"""Data Validation Engine for DataGuard AI.

Evaluates datasets against configurable data quality rules including
required columns, non-null assertions, uniqueness, numeric ranges,
and allowed categorical values.
"""

from typing import List, Optional
import pandas as pd

from app.core.logging import get_logger
from app.schemas.validation import (
    ColumnRule,
    SeverityLevel,
    ValidationConfig,
    ValidationReport,
    ValidationResult,
    ValidationRuleType,
)

logger = get_logger(__name__)


def get_default_transaction_rules() -> ValidationConfig:
    """Create default quality rules for financial transaction datasets."""
    return ValidationConfig(
        required_columns=[
            "transaction_id",
            "customer_id",
            "transaction_date",
            "amount",
            "payment_method",
        ],
        column_rules=[
            ColumnRule(
                column="transaction_id",
                required=True,
                unique=True,
                severity=SeverityLevel.ERROR,
            ),
            ColumnRule(
                column="customer_id",
                required=True,
                severity=SeverityLevel.ERROR,
            ),
            ColumnRule(
                column="transaction_date",
                required=True,
                severity=SeverityLevel.ERROR,
            ),
            ColumnRule(
                column="amount",
                required=True,
                min_value=0.0,
                severity=SeverityLevel.ERROR,
            ),
            ColumnRule(
                column="payment_method",
                required=True,
                allowed_values=["Credit Card", "UPI", "Debit Card", "Net Banking", "Wallet"],
                severity=SeverityLevel.ERROR,
            ),
        ],
    )


class DataValidator:
    """Validator that checks DataFrames against configurable data quality rules."""

    def validate(
        self,
        df: pd.DataFrame,
        config: Optional[ValidationConfig] = None,
    ) -> ValidationReport:
        """Validate a pandas DataFrame against quality rules.

        The original DataFrame is never modified.

        Args:
            df: Input pandas DataFrame to validate.
            config: Optional custom validation configuration. If None,
                    standard transaction quality rules are used.

        Returns:
            ValidationReport: Summary and detailed results for all evaluated rules.
        """
        if config is None:
            config = get_default_transaction_rules()

        results: List[ValidationResult] = []

        # 1. Schema / Required Columns Check
        if config.required_columns:
            for required_col in config.required_columns:
                is_present = required_col in df.columns
                results.append(
                    ValidationResult(
                        rule=ValidationRuleType.SCHEMA.value,
                        column=required_col,
                        passed=is_present,
                        violations=0 if is_present else 1,
                        severity=SeverityLevel.ERROR.value,
                        message=(
                            f"Required column '{required_col}' is present"
                            if is_present
                            else f"Required column '{required_col}' is missing from the dataset"
                        ),
                    )
                )

        # 2. Column-Level Rule Checks
        for rule in config.column_rules:
            col_name = rule.column
            severity_str = rule.severity.value if hasattr(rule.severity, "value") else str(rule.severity)

            # If column does not exist, required / uniqueness / value checks cannot be executed
            if col_name not in df.columns:
                continue

            series = df[col_name]

            # (A) Required / Non-null check
            if rule.required:
                missing_count = int(series.isna().sum())
                passed = missing_count == 0
                results.append(
                    ValidationResult(
                        rule=ValidationRuleType.REQUIRED.value,
                        column=col_name,
                        passed=passed,
                        violations=missing_count,
                        severity=severity_str,
                        message=(
                            f"All records contain non-null values in '{col_name}'"
                            if passed
                            else f"{missing_count} record(s) contain missing/null values in '{col_name}'"
                        ),
                    )
                )

            # (B) Uniqueness check
            if rule.unique:
                non_null_series = series.dropna()
                duplicate_count = int(non_null_series.duplicated().sum())
                passed = duplicate_count == 0
                results.append(
                    ValidationResult(
                        rule=ValidationRuleType.UNIQUE.value,
                        column=col_name,
                        passed=passed,
                        violations=duplicate_count,
                        severity=severity_str,
                        message=(
                            f"All values in '{col_name}' are unique"
                            if passed
                            else f"{duplicate_count} duplicate record(s) found in '{col_name}'"
                        ),
                    )
                )

            # (C) Numeric range check
            if rule.min_value is not None or rule.max_value is not None:
                numeric_series = pd.to_numeric(series.dropna(), errors="coerce")
                violations = 0

                if rule.min_value is not None and rule.max_value is not None:
                    range_mask = (numeric_series < rule.min_value) | (numeric_series > rule.max_value)
                    violations = int(range_mask.sum())
                    range_desc = f"[{rule.min_value}, {rule.max_value}]"
                elif rule.min_value is not None:
                    range_mask = numeric_series < rule.min_value
                    violations = int(range_mask.sum())
                    range_desc = f">= {rule.min_value}"
                elif rule.max_value is not None:
                    range_mask = numeric_series > rule.max_value
                    violations = int(range_mask.sum())
                    range_desc = f"<= {rule.max_value}"

                passed = violations == 0
                results.append(
                    ValidationResult(
                        rule=ValidationRuleType.NUMERIC_RANGE.value,
                        column=col_name,
                        passed=passed,
                        violations=violations,
                        severity=severity_str,
                        message=(
                            f"All values in '{col_name}' satisfy range constraint ({range_desc})"
                            if passed
                            else f"{violations} record(s) in '{col_name}' violate range constraint ({range_desc})"
                        ),
                    )
                )

            # (D) Allowed categorical values check
            if rule.allowed_values is not None:
                non_null_series = series.dropna()
                # Coerce allowed values and series items for consistent matching
                allowed_set = set(rule.allowed_values)
                invalid_mask = ~non_null_series.isin(allowed_set)
                violations = int(invalid_mask.sum())
                passed = violations == 0
                results.append(
                    ValidationResult(
                        rule=ValidationRuleType.ALLOWED_VALUES.value,
                        column=col_name,
                        passed=passed,
                        violations=violations,
                        severity=severity_str,
                        message=(
                            f"All values in '{col_name}' belong to allowed set"
                            if passed
                            else f"{violations} record(s) in '{col_name}' contain values not in allowed set: {rule.allowed_values}"
                        ),
                    )
                )

        total_rules = len(results)
        passed_rules = sum(1 for r in results if r.passed)
        failed_rules = total_rules - passed_rules
        is_valid = failed_rules == 0

        logger.info(
            "Validation completed: %d total rules, %d passed, %d failed (is_valid=%s)",
            total_rules,
            passed_rules,
            failed_rules,
            is_valid,
        )

        return ValidationReport(
            total_rules=total_rules,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            is_valid=is_valid,
            results=results,
        )
