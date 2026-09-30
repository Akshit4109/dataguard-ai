"""Pydantic schemas for data quality validation rules and results."""

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    """Severity levels for validation rules."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationRuleType(str, Enum):
    """Supported data validation rule types."""

    SCHEMA = "schema"
    REQUIRED = "required"
    UNIQUE = "unique"
    NUMERIC_RANGE = "numeric_range"
    ALLOWED_VALUES = "allowed_values"


class ColumnRule(BaseModel):
    """Configurable quality validation rule for a specific column."""

    column: str = Field(description="Target column name to validate")
    required: bool = Field(default=False, description="Whether column must not contain null/empty values")
    unique: bool = Field(default=False, description="Whether all values in column must be unique")
    min_value: Optional[float] = Field(default=None, description="Minimum allowed numeric value")
    max_value: Optional[float] = Field(default=None, description="Maximum allowed numeric value")
    allowed_values: Optional[List[Any]] = Field(
        default=None,
        description="List of allowed discrete values for categorical columns",
    )
    severity: SeverityLevel = Field(
        default=SeverityLevel.ERROR,
        description="Severity level if rule fails",
    )


class ValidationConfig(BaseModel):
    """Complete validation configuration containing schema and column rules."""

    required_columns: Optional[List[str]] = Field(
        default=None,
        description="List of column names that must exist in the dataset",
    )
    column_rules: List[ColumnRule] = Field(
        default_factory=list,
        description="List of column-level validation rules",
    )


class ValidationResult(BaseModel):
    """Result of an individual validation rule check."""

    rule: str = Field(description="Name of the validation rule (e.g. required, unique, numeric_range)")
    column: str = Field(description="Target column name")
    passed: bool = Field(description="Whether the validation rule passed")
    violations: int = Field(description="Number of violating records or discrepancies")
    severity: str = Field(description="Severity level (ERROR, WARNING, INFO)")
    message: str = Field(description="Human-readable explanation of the validation result")


class ValidationReport(BaseModel):
    """Comprehensive dataset validation report."""

    total_rules: int = Field(description="Total number of validation rules evaluated")
    passed_rules: int = Field(description="Number of rules that passed")
    failed_rules: int = Field(description="Number of rules that failed")
    is_valid: bool = Field(description="True if all rules passed with zero violations")
    results: List[ValidationResult] = Field(
        default_factory=list,
        description="Detailed list of individual rule validation results",
    )
