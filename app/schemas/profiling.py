"""Pydantic schemas for data profiling results."""

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class LogicalType(str, Enum):
    """Logical classification categories for dataset columns."""

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    UNKNOWN = "unknown"


class NumericStatistics(BaseModel):
    """Descriptive statistics for numeric columns."""

    min: Optional[float] = Field(default=None, description="Minimum numeric value")
    max: Optional[float] = Field(default=None, description="Maximum numeric value")
    mean: Optional[float] = Field(default=None, description="Arithmetic mean of values")
    median: Optional[float] = Field(default=None, description="Median (50th percentile) value")
    std: Optional[float] = Field(default=None, description="Sample standard deviation")
    percentile_25: Optional[float] = Field(default=None, description="25th percentile (Q1)")
    percentile_50: Optional[float] = Field(default=None, description="50th percentile (Q2 / Median)")
    percentile_75: Optional[float] = Field(default=None, description="75th percentile (Q3)")


class CategoricalStatistics(BaseModel):
    """Distribution statistics for categorical/object/boolean columns."""

    most_frequent_value: Optional[Any] = Field(
        default=None,
        description="The most frequently occurring value in the column",
    )
    most_frequent_count: Optional[int] = Field(
        default=None,
        description="Occurrence count of the most frequent value",
    )
    unique_count: int = Field(
        default=0,
        description="Number of distinct non-null values",
    )


class DatetimeStatistics(BaseModel):
    """Temporal range statistics for datetime columns."""

    min_date: Optional[str] = Field(
        default=None,
        description="Earliest timestamp in ISO 8601 or string format",
    )
    max_date: Optional[str] = Field(
        default=None,
        description="Latest timestamp in ISO 8601 or string format",
    )


class ColumnProfile(BaseModel):
    """Profiling analysis report for a single column."""

    name: str = Field(description="Column name")
    data_type: str = Field(description="Underlying pandas/numpy data type")
    logical_type: str = Field(description="Logical classification (numeric, categorical, boolean, datetime, unknown)")
    row_count: int = Field(description="Total rows in the column")
    non_null_count: int = Field(description="Count of non-null / valid values")
    missing_count: int = Field(description="Count of null / NaN / NA values")
    missing_percentage: float = Field(description="Percentage of missing values (0.0 to 100.0)")
    unique_count: int = Field(description="Count of distinct non-null values")
    unique_percentage: float = Field(description="Percentage of unique values relative to row count (0.0 to 100.0)")

    # Specialized stats (populated based on logical_type)
    numeric_stats: Optional[NumericStatistics] = Field(
        default=None,
        description="Numeric summary statistics if column is numeric",
    )
    categorical_stats: Optional[CategoricalStatistics] = Field(
        default=None,
        description="Categorical summary statistics if column is categorical or boolean",
    )
    datetime_stats: Optional[DatetimeStatistics] = Field(
        default=None,
        description="Datetime range statistics if column is datetime",
    )


class DatasetProfile(BaseModel):
    """Comprehensive dataset-level and column-level profiling report."""

    row_count: int = Field(description="Total number of rows in the dataset")
    column_count: int = Field(description="Total number of columns in the dataset")
    total_cells: int = Field(description="Total cells (row_count * column_count)")
    duplicate_rows: int = Field(description="Count of duplicate rows")
    duplicate_percentage: float = Field(description="Percentage of duplicate rows (0.0 to 100.0)")
    total_missing_values: int = Field(description="Total count of missing values across all cells")
    missing_percentage: float = Field(description="Percentage of missing values across all cells (0.0 to 100.0)")
    numeric_columns: int = Field(description="Count of numeric columns")
    categorical_columns: int = Field(description="Count of categorical columns")
    boolean_columns: int = Field(description="Count of boolean columns")
    datetime_columns: int = Field(description="Count of datetime columns")
    unknown_columns: int = Field(description="Count of unclassified/unknown columns")
    columns: List[ColumnProfile] = Field(
        default_factory=list,
        description="Detailed profiling results for each individual column",
    )
