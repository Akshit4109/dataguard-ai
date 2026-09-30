"""Unsupervised ML Anomaly Detection Engine for DataGuard AI.

Uses Scikit-learn's Isolation Forest to identify statistically unusual
records across numeric features in structured datasets.
"""

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.core.logging import get_logger
from app.schemas.anomaly import (
    AnomalyDetectionReport,
    AnomalyRecord,
    AnomalyStatus,
)

logger = get_logger(__name__)

# Common identifier column patterns to exclude from ML features
IDENTIFIER_COLUMNS = {"id", "transaction_id", "customer_id", "user_id", "account_id", "session_id"}


class AnomalyDetector:
    """Unsupervised anomaly detector utilizing Scikit-learn's Isolation Forest algorithm."""

    def __init__(
        self,
        contamination: Union[float, str] = 0.05,
        random_state: int = 42,
    ) -> None:
        """Initialize the AnomalyDetector.

        Args:
            contamination: Expected proportion of outliers in the data (e.g. 0.05 for 5% or 'auto').
            random_state: Seed for reproducible tree partition generation.
        """
        self.contamination = contamination
        self.random_state = random_state

    def _select_numeric_features(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
    ) -> List[str]:
        """Identify suitable numeric features, filtering out identifier columns."""
        if feature_cols is not None:
            # Validate user-provided feature columns exist and are numeric
            valid_cols = []
            for col in feature_cols:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col].dtype):
                    valid_cols.append(col)
                elif col in df.columns:
                    # Attempt numeric coercion check
                    converted = pd.to_numeric(df[col].dropna(), errors="coerce")
                    if not converted.empty and converted.notna().sum() > 0:
                        valid_cols.append(col)
            return valid_cols

        selected: List[str] = []
        for col in df.columns:
            col_str = str(col).lower()
            if col_str in IDENTIFIER_COLUMNS or col_str.endswith("_id"):
                continue

            if pd.api.types.is_numeric_dtype(df[col].dtype) and not pd.api.types.is_bool_dtype(df[col].dtype):
                selected.append(str(col))

        return selected

    def detect_anomalies(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
    ) -> AnomalyDetectionReport:
        """Execute Isolation Forest anomaly detection on the input DataFrame.

        The original DataFrame is never modified.

        Args:
            df: The pandas DataFrame to evaluate.
            feature_cols: Optional list of numeric column names to use as features.

        Returns:
            AnomalyDetectionReport: Summary of detected anomalies and list of anomalous records.

        Raises:
            ValueError: If the dataset is empty or contains insufficient numeric data for ML.
        """
        total_records = len(df)
        if total_records == 0:
            return AnomalyDetectionReport(
                total_records=0,
                anomaly_count=0,
                anomaly_percentage=0.0,
                features_used=[],
                anomalies=[],
            )

        features = self._select_numeric_features(df, feature_cols)
        if not features:
            logger.warning("No suitable numeric features found for anomaly detection")
            return AnomalyDetectionReport(
                total_records=total_records,
                anomaly_count=0,
                anomaly_percentage=0.0,
                features_used=[],
                anomalies=[],
            )

        # Prepare feature matrix safely with imputation for missing values
        X = pd.DataFrame(index=df.index)
        for col in features:
            col_numeric = pd.to_numeric(df[col], errors="coerce")
            # Impute missing values with column median, fallback to 0.0 if all null
            median_val = col_numeric.median()
            fill_val = 0.0 if pd.isna(median_val) else float(median_val)
            X[col] = col_numeric.fillna(fill_val)

        # Require at least 2 samples to fit IsolationForest
        if len(X) < 2:
            return AnomalyDetectionReport(
                total_records=total_records,
                anomaly_count=0,
                anomaly_percentage=0.0,
                features_used=features,
                anomalies=[],
            )

        try:
            model = IsolationForest(
                contamination=self.contamination,
                random_state=self.random_state,
                n_estimators=100,
            )
            # fit_predict returns: 1 for inliers (NORMAL), -1 for outliers (ANOMALY)
            predictions = model.fit_predict(X)
            # decision_function returns average anomaly score (lower is more anomalous)
            scores = model.decision_function(X)
        except Exception as err:
            logger.error("Error running Isolation Forest: %s", err, exc_info=True)
            raise ValueError(f"Failed to run anomaly detection: {str(err)}") from err

        anomalous_records: List[AnomalyRecord] = []
        id_column = next((col for col in ["transaction_id", "id", "customer_id"] if col in df.columns), None)

        for idx, (pred, score) in enumerate(zip(predictions, scores)):
            is_anomaly = pred == -1
            if is_anomaly:
                rec_id = str(df.iloc[idx][id_column]) if id_column and pd.notna(df.iloc[idx][id_column]) else None
                feat_dict: Dict[str, Any] = {}
                for col in features:
                    val = df.iloc[idx][col]
                    feat_dict[col] = None if pd.isna(val) else float(val) if isinstance(val, (int, float, np.number)) else str(val)

                anomalous_records.append(
                    AnomalyRecord(
                        row_index=idx,
                        record_id=rec_id,
                        anomaly_score=round(float(score), 4),
                        status=AnomalyStatus.ANOMALY,
                        is_anomaly=True,
                        features=feat_dict,
                    )
                )

        anomaly_count = len(anomalous_records)
        anomaly_percentage = round((anomaly_count / total_records) * 100, 2) if total_records > 0 else 0.0

        logger.info(
            "Anomaly detection complete: %d records evaluated, %d anomalies detected (%.2f%%)",
            total_records,
            anomaly_count,
            anomaly_percentage,
        )

        return AnomalyDetectionReport(
            total_records=total_records,
            anomaly_count=anomaly_count,
            anomaly_percentage=anomaly_percentage,
            features_used=features,
            anomalies=anomalous_records,
        )
