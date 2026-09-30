"""SQLAlchemy model for Reports storage."""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class Report(Base):
    """Reports table storing analysis results, scores, and complete report payloads."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    missing_values = Column(Integer, nullable=False, default=0)
    duplicate_rows = Column(Integer, nullable=False, default=0)
    validation_violations = Column(Integer, nullable=False, default=0)
    anomalies = Column(Integer, nullable=False, default=0)
    health_score = Column(Float, nullable=False)
    health_status = Column(String(50), nullable=False)
    report_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    # Relationship to parent dataset
    dataset = relationship("Dataset", back_populates="reports")
