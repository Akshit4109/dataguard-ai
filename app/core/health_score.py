"""Data Health Score Calculator & Combined Report Generator for DataGuard AI.

Synthesizes metrics from profiling, validation, and ML anomaly detection
into a standardized quality score (0-100), health classification,
and actionable rule-based recommendations.
"""

from typing import List, Optional
import pandas as pd

from app.core.anomaly_detector import AnomalyDetector
from app.core.logging import get_logger
from app.core.profiler import DataProfiler
from app.core.validator import DataValidator
from app.schemas.anomaly import AnomalyDetectionReport
from app.schemas.health import (
    DataGuardReport,
    HealthStatus,
    ReportSummary,
    ScoreBreakdown,
)
from app.schemas.profiling import DatasetProfile
from app.schemas.validation import ValidationConfig, ValidationReport

logger = get_logger(__name__)


class HealthScoreCalculator:
    """Calculates overall dataset health scores and compiles full analysis reports."""

    # Transparent quality component weightings (sum to 1.0)
    WEIGHT_COMPLETENESS = 0.30   # 30%: Missing values & null rate
    WEIGHT_VALIDATION = 0.30     # 30%: Validation rule passing rate
    WEIGHT_UNIQUENESS = 0.20     # 20%: Duplicate rows & redundancy rate
    WEIGHT_ANOMALY = 0.20        # 20%: Statistical outlier / anomaly rate

    def calculate(
        self,
        profile: DatasetProfile,
        validation: ValidationReport,
        anomalies: AnomalyDetectionReport,
        include_details: bool = True,
    ) -> DataGuardReport:
        """Compute the combined health score and compile the complete DataGuard report.

        Args:
            profile: Dataset profiling results.
            validation: Data quality validation results.
            anomalies: ML anomaly detection results.
            include_details: Whether to include nested profiling, validation, and anomaly reports.

        Returns:
            DataGuardReport: Synthesized report containing health score, status, summary,
                             score breakdown, recommendations, and optional deep-dive details.
        """
        # 1. Completeness Score (30% weight)
        completeness_score = max(0.0, min(100.0, 100.0 - profile.missing_percentage))

        # 2. Validation Quality Score (30% weight)
        if validation.total_rules > 0:
            validation_score = (validation.passed_rules / validation.total_rules) * 100.0
        else:
            validation_score = 100.0
        validation_score = max(0.0, min(100.0, validation_score))

        # 3. Uniqueness Quality Score (20% weight)
        uniqueness_score = max(0.0, min(100.0, 100.0 - profile.duplicate_percentage))

        # 4. Anomaly Quality Score (20% weight)
        anomaly_score = max(0.0, min(100.0, 100.0 - anomalies.anomaly_percentage))

        # Calculate overall weighted score
        raw_score = (
            (self.WEIGHT_COMPLETENESS * completeness_score)
            + (self.WEIGHT_VALIDATION * validation_score)
            + (self.WEIGHT_UNIQUENESS * uniqueness_score)
            + (self.WEIGHT_ANOMALY * anomaly_score)
        )
        health_score = round(max(0.0, min(100.0, raw_score)), 2)

        # Classify Health Status
        if health_score >= 90.0:
            status = HealthStatus.EXCELLENT
        elif health_score >= 75.0:
            status = HealthStatus.GOOD
        elif health_score >= 50.0:
            status = HealthStatus.NEEDS_ATTENTION
        else:
            status = HealthStatus.POOR

        # Total violation count from validation
        total_violations = sum(r.violations for r in validation.results if not r.passed)

        # Build concise metrics summary
        summary = ReportSummary(
            rows=profile.row_count,
            columns=profile.column_count,
            missing_values=profile.total_missing_values,
            duplicates=profile.duplicate_rows,
            validation_violations=total_violations,
            anomalies=anomalies.anomaly_count,
        )

        # Build component score breakdown
        breakdown = ScoreBreakdown(
            completeness_score=round(completeness_score, 2),
            validation_score=round(validation_score, 2),
            uniqueness_score=round(uniqueness_score, 2),
            anomaly_score=round(anomaly_score, 2),
        )

        # Generate rule-based recommendations
        recommendations = self._generate_recommendations(profile, validation, anomalies)

        logger.info(
            "Health score computed: %.2f [%s] (Completeness=%.2f, Validation=%.2f, Uniqueness=%.2f, Anomaly=%.2f)",
            health_score,
            status.value,
            completeness_score,
            validation_score,
            uniqueness_score,
            anomaly_score,
        )

        return DataGuardReport(
            health_score=health_score,
            status=status,
            summary=summary,
            score_breakdown=breakdown,
            recommendations=recommendations,
            profile=profile if include_details else None,
            validation=validation if include_details else None,
            anomalies=anomalies if include_details else None,
        )

    def generate_report(
        self,
        df: pd.DataFrame,
        validation_config: Optional[ValidationConfig] = None,
        include_details: bool = True,
    ) -> DataGuardReport:
        """Convenience method to execute full DataGuard pipeline on a DataFrame.

        Orchestrates DataProfiler, DataValidator, AnomalyDetector, and HealthScoreCalculator.

        Args:
            df: The pandas DataFrame to analyze.
            validation_config: Optional custom validation configuration.
            include_details: Whether to embed full sub-reports.

        Returns:
            DataGuardReport: Full combined analysis report.
        """
        profiler = DataProfiler()
        validator = DataValidator()
        detector = AnomalyDetector()

        profile = profiler.profile(df)
        validation = validator.validate(df, config=validation_config)
        anomalies = detector.detect_anomalies(df)

        return self.calculate(
            profile=profile,
            validation=validation,
            anomalies=anomalies,
            include_details=include_details,
        )

    def _generate_recommendations(
        self,
        profile: DatasetProfile,
        validation: ValidationReport,
        anomalies: AnomalyDetectionReport,
    ) -> List[str]:
        """Generate clear, actionable, rule-based data quality recommendations."""
        recs: List[str] = []

        # 1. Missing values recommendations
        if profile.total_missing_values > 0:
            missing_cols = [c.name for c in profile.columns if c.missing_count > 0]
            cols_str = ", ".join(missing_cols[:3]) + ("..." if len(missing_cols) > 3 else "")
            recs.append(
                f"Review and clean/impute {profile.total_missing_values} missing value(s) found in: {cols_str}."
            )

        # 2. Duplicate records recommendations
        if profile.duplicate_rows > 0:
            recs.append(
                f"Investigate and deduplicate {profile.duplicate_rows} duplicate record(s) ({profile.duplicate_percentage}% of dataset)."
            )

        # 3. Validation violations recommendations
        if validation.failed_rules > 0:
            failed_rules_summary = [f"{r.column} ({r.rule})" for r in validation.results if not r.passed]
            rules_str = ", ".join(failed_rules_summary[:3]) + ("..." if len(failed_rules_summary) > 3 else "")
            recs.append(
                f"Resolve {validation.failed_rules} failing validation quality rule(s) for: {rules_str}."
            )

        # 4. Anomaly detection recommendations
        if anomalies.anomaly_count > 0:
            recs.append(
                f"Inspect {anomalies.anomaly_count} statistically anomalous transaction record(s) flagged by Isolation Forest."
            )

        # 5. Perfect dataset feedback
        if not recs:
            recs.append("Dataset quality is excellent with no missing values, duplicates, validation failures, or anomalies detected.")

        return recs
