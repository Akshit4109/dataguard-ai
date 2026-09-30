"""SQLAlchemy model for Datasets metadata."""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class Dataset(Base):
    """Dataset table storing file metadata and high-level health metrics."""

    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False, index=True)
    row_count = Column(Integer, nullable=False)
    column_count = Column(Integer, nullable=False)
    health_score = Column(Float, nullable=False)
    health_status = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    # One-to-many relationship with reports
    reports = relationship(
        "Report",
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="desc(Report.created_at)",
    )
