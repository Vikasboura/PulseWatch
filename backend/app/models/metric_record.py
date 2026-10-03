from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, Integer, String, Float, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class MetricRecord(Base):
    __tablename__ = "metric_records"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    labels = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    project = relationship("Project", back_populates="metrics")

    __table_args__ = (
        Index("idx_metrics_project_name_time", "project_id", "name", timestamp.desc()),
    )
