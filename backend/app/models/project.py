import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    retention_days = Column(Integer, default=30, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    owner = relationship("User", back_populates="projects")
    api_keys = relationship("ApiKey", back_populates="project", cascade="all, delete-orphan")
    logs = relationship("LogRecord", back_populates="project", cascade="all, delete-orphan")
    metrics = relationship("MetricRecord", back_populates="project", cascade="all, delete-orphan")
    alert_rules = relationship("AlertRule", back_populates="project", cascade="all, delete-orphan")
    alert_events = relationship("AlertEvent", back_populates="project", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    key_prefix = Column(String(12), nullable=False)  # e.g., "pw_live_a1b2"
    key_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA-256
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    project = relationship("Project", back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_lookup", "key_hash", "is_active"),
    )
