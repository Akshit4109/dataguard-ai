"""Data Profiling Engine for DataGuard AI.

Analyzes dataset structure, completeness, uniqueness, duplicates,
data types, and column-level summary statistics.
"""

from typing import Any, Optional
import numpy as np
import pandas as pd

from app.core.logging import get_logger
from app.schemas.profiling import (
    CategoricalStatistics,
    ColumnProfile,
    DatasetProfile,
    DatetimeStatistics,
    LogicalType,
    NumericStatistics,
)

logger = get_logger(__name__)


class DataProfiler:
    """Independent engine for profiling structured pandas DataFrames."""

    def profile(self, df: pd.DataFrame) -> DatasetProfile:
        """Perform comprehensive data profiling on the input DataFrame.

        The original DataFrame is never modified.

        Args:
            df: The pandas DataFrame to profile.

        Returns:
            DatasetProfile: Structured profiling report containing dataset-level
                            and column-level metrics.
        """
        row_count = int(len(df))
        column_count = int(len(df.columns))
        total_cells = row_count * column_count

        if row_count == 0 or column_count == 0:
            return self._profile_empty_dataframe(df, row_count, column_count)

        # Dataset-level duplicate analysis
        try:
            duplicate_rows = int(df.duplicated().sum())
            duplicate_percentage = round((duplicate_rows / row_count) * 100, 2)
        except Exception as err:
            logger.warning("Error calculating duplicate rows: %s", err)
            duplicate_rows = 0
            duplicate_percentage = 0.0

        # Dataset-level missing values analysis
        try:
            total_missing = int(df.isna().sum().sum())
            missing_percentage = round((total_missing / total_cells) * 100, 2) if total_cells > 0 else 0.0
        except Exception as err:
            logger.warning("Error calculating total missing values: %s", err)
            total_missing = 0
            missing_percentage = 0.0

        column_profiles = []
        numeric_cols_count = 0
        categorical_cols_count = 0
        boolean_cols_count = 0
        datetime_cols_count = 0
        unknown_cols_count = 0

        for col_name in df.columns:
            series = df[col_name]
            col_profile = self._profile_column(str(col_name), series, row_count)
            column_profiles.append(col_profile)

            if col_profile.logical_type == LogicalType.NUMERIC.value:
                numeric_cols_count += 1
            elif col_profile.logical_type == LogicalType.CATEGORICAL.value:
                categorical_cols_count += 1
            elif col_profile.logical_type == LogicalType.BOOLEAN.value:
                boolean_cols_count += 1
            elif col_profile.logical_type == LogicalType.DATETIME.value:
                datetime_cols_count += 1
            else:
                unknown_cols_count += 1

        return DatasetProfile(
            row_count=row_count,
            column_count=column_count,
            total_cells=total_cells,
            duplicate_rows=duplicate_rows,
            duplicate_percentage=duplicate_percentage,
            total_missing_values=total_missing,
            missing_percentage=missing_percentage,
            numeric_columns=numeric_cols_count,
            categorical_columns=categorical_cols_count,
            boolean_columns=boolean_cols_count,
            datetime_columns=datetime_cols_count,
            unknown_columns=unknown_cols_count,
            columns=column_profiles,
        )

    def _profile_empty_dataframe(self, df: pd.DataFrame, row_count: int, column_count: int) -> DatasetProfile:
        """Handle empty DataFrame gracefully."""
        column_profiles = []
        for col_name in df.columns:
            series = df[col_name]
            logical_type = self._classify_logical_type(series)
            column_profiles.append(
                ColumnProfile(
                    name=str(col_name),
                    data_type=str(series.dtype),
                    logical_type=logical_type.value,
                    row_count=row_count,
                    non_null_count=0,
                    missing_count=0,
                    missing_percentage=0.0,
                    unique_count=0,
                    unique_percentage=0.0,
                    numeric_stats=NumericStatistics() if logical_type == LogicalType.NUMERIC else None,
                    categorical_stats=(
                        CategoricalStatistics(unique_count=0)
                        if logical_type in (LogicalType.CATEGORICAL, LogicalType.BOOLEAN)
                        else None
                    ),
                    datetime_stats=DatetimeStatistics() if logical_type == LogicalType.DATETIME else None,
                )
            )

        numeric_count = sum(1 for c in column_profiles if c.logical_type == LogicalType.NUMERIC.value)
        cat_count = sum(1 for c in column_profiles if c.logical_type == LogicalType.CATEGORICAL.value)
        bool_count = sum(1 for c in column_profiles if c.logical_type == LogicalType.BOOLEAN.value)
        dt_count = sum(1 for c in column_profiles if c.logical_type == LogicalType.DATETIME.value)
        unk_count = sum(1 for c in column_profiles if c.logical_type == LogicalType.UNKNOWN.value)

        return DatasetProfile(
            row_count=row_count,
            column_count=column_count,
            total_cells=0,
            duplicate_rows=0,
            duplicate_percentage=0.0,
            total_missing_values=0,
            missing_percentage=0.0,
            numeric_columns=numeric_count,
            categorical_columns=cat_count,
            boolean_columns=bool_count,
            datetime_columns=dt_count,
            unknown_columns=unk_count,
            columns=column_profiles,
        )

    def _classify_logical_type(self, series: pd.Series) -> LogicalType:
        """Classify series into logical types: numeric, categorical, boolean, datetime, unknown."""
        dtype = series.dtype

        # 1. Check boolean first (some boolean types might otherwise register as numeric or object)
        if pd.api.types.is_bool_dtype(dtype) or dtype == bool or isinstance(dtype, pd.BooleanDtype):
            return LogicalType.BOOLEAN

        # 2. Check datetime (only if already reliable datetime dtype)
        if pd.api.types.is_datetime64_any_dtype(dtype) or isinstance(dtype, pd.DatetimeTZDtype):
            return LogicalType.DATETIME

        # 3. Check numeric (integers, floats)
        if pd.api.types.is_numeric_dtype(dtype):
            return LogicalType.NUMERIC

        # 4. Check categorical / string / object
        if (
            isinstance(dtype, pd.CategoricalDtype)
            or pd.api.types.is_string_dtype(dtype)
            or pd.api.types.is_object_dtype(dtype)
        ):
            return LogicalType.CATEGORICAL

        return LogicalType.UNKNOWN

    def _profile_column(self, col_name: str, series: pd.Series, row_count: int) -> ColumnProfile:
        """Analyze completeness, uniqueness, and statistics for an individual column."""
        logical_type = self._classify_logical_type(series)
        data_type_str = str(series.dtype)

        # Completeness metrics
        missing_count = int(series.isna().sum())
        non_null_count = int(row_count - missing_count)
        missing_percentage = round((missing_count / row_count) * 100, 2) if row_count > 0 else 0.0

        # Uniqueness metrics
        try:
            unique_count = int(series.nunique(dropna=True))
        except Exception:
            unique_count = 0
        unique_percentage = round((unique_count / row_count) * 100, 2) if row_count > 0 else 0.0

        # Type-specific statistics
        numeric_stats: Optional[NumericStatistics] = None
        categorical_stats: Optional[CategoricalStatistics] = None
        datetime_stats: Optional[DatetimeStatistics] = None

        if logical_type == LogicalType.NUMERIC:
            numeric_stats = self._calculate_numeric_stats(series, non_null_count)
        elif logical_type in (LogicalType.CATEGORICAL, LogicalType.BOOLEAN):
            categorical_stats = self._calculate_categorical_stats(series, non_null_count, unique_count)
        elif logical_type == LogicalType.DATETIME:
            datetime_stats = self._calculate_datetime_stats(series, non_null_count)

        return ColumnProfile(
            name=col_name,
            data_type=data_type_str,
            logical_type=logical_type.value,
            row_count=row_count,
            non_null_count=non_null_count,
            missing_count=missing_count,
            missing_percentage=missing_percentage,
            unique_count=unique_count,
            unique_percentage=unique_percentage,
            numeric_stats=numeric_stats,
            categorical_stats=categorical_stats,
            datetime_stats=datetime_stats,
        )

    def _calculate_numeric_stats(self, series: pd.Series, non_null_count: int) -> NumericStatistics:
        """Compute summary statistics for a numeric column safely."""
        if non_null_count == 0:
            return NumericStatistics()

        try:
            valid_series = pd.to_numeric(series.dropna(), errors="coerce").dropna()
            if valid_series.empty:
                return NumericStatistics()

            min_val = float(valid_series.min())
            max_val = float(valid_series.max())
            mean_val = round(float(valid_series.mean()), 4)
            median_val = round(float(valid_series.median()), 4)

            std_val: Optional[float] = None
            if len(valid_series) > 1:
                calc_std = valid_series.std()
                if not pd.isna(calc_std):
                    std_val = round(float(calc_std), 4)
            elif len(valid_series) == 1:
                std_val = 0.0

            q25 = round(float(valid_series.quantile(0.25)), 4)
            q50 = round(float(valid_series.quantile(0.50)), 4)
            q75 = round(float(valid_series.quantile(0.75)), 4)

            return NumericStatistics(
                min=min_val,
                max=max_val,
                mean=mean_val,
                median=median_val,
                std=std_val,
                percentile_25=q25,
                percentile_50=q50,
                percentile_75=q75,
            )
        except Exception as err:
            logger.warning("Error calculating numeric statistics: %s", err)
            return NumericStatistics()

    def _calculate_categorical_stats(
        self, series: pd.Series, non_null_count: int, unique_count: int
    ) -> CategoricalStatistics:
        """Compute frequency statistics for a categorical or boolean column safely."""
        if non_null_count == 0:
            return CategoricalStatistics(
                most_frequent_value=None,
                most_frequent_count=None,
                unique_count=0,
            )

        try:
            valid_series = series.dropna()
            val_counts = valid_series.value_counts()
            if val_counts.empty:
                return CategoricalStatistics(unique_count=unique_count)

            raw_top_val = val_counts.index[0]
            # Convert numpy types to native Python types for clean JSON serialization
            if isinstance(raw_top_val, (np.bool_, bool)):
                top_val: Any = bool(raw_top_val)
            elif isinstance(raw_top_val, (np.integer, int)):
                top_val = int(raw_top_val)
            elif isinstance(raw_top_val, (np.floating, float)):
                top_val = float(raw_top_val)
            else:
                top_val = str(raw_top_val)

            top_count = int(val_counts.iloc[0])

            return CategoricalStatistics(
                most_frequent_value=top_val,
                most_frequent_count=top_count,
                unique_count=unique_count,
            )
        except Exception as err:
            logger.warning("Error calculating categorical statistics: %s", err)
            return CategoricalStatistics(unique_count=unique_count)

    def _calculate_datetime_stats(self, series: pd.Series, non_null_count: int) -> DatetimeStatistics:
        """Compute date range statistics for a datetime column safely."""
        if non_null_count == 0:
            return DatetimeStatistics(min_date=None, max_date=None)

        try:
            valid_series = series.dropna()
            if valid_series.empty:
                return DatetimeStatistics(min_date=None, max_date=None)

            min_val = valid_series.min()
            max_val = valid_series.max()

            min_date = min_val.isoformat() if hasattr(min_val, "isoformat") else str(min_val)
            max_date = max_val.isoformat() if hasattr(max_val, "isoformat") else str(max_val)

            return DatetimeStatistics(min_date=min_date, max_date=max_date)
        except Exception as err:
            logger.warning("Error calculating datetime statistics: %s", err)
            return DatetimeStatistics(min_date=None, max_date=None)
