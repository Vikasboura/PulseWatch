from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class LogRecord(Base):
    __tablename__ = "log_records"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    level = Column(String(16), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    # Renamed attribute from 'metadata' to avoid SQLAlchemy reserved property collision
    log_metadata = Column("log_metadata", JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    project = relationship("Project", back_populates="logs")

    __table_args__ = (
        Index("idx_logs_project_time", "project_id", timestamp.desc()),
        Index("idx_logs_project_level_time", "project_id", "level", timestamp.desc()),
    )
