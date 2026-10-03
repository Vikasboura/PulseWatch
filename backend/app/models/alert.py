import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Index, JSON, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    rule_type = Column(String(32), nullable=False)          # 'error_count' or 'metric_threshold'
    target_metric = Column(String(100), nullable=True)      # metric name if metric_threshold
    condition_operator = Column(String(4), nullable=False)  # '>', '>=', '<', '<='
    threshold = Column(Float, nullable=False)
    window_minutes = Column(Integer, default=5, nullable=False)
    channel_type = Column(String(16), nullable=False)       # 'email' or 'slack'
    channel_config = Column(JSON, default=dict, nullable=False) # {"email": "..."} or {"webhook_url": "..."}
    is_active = Column(Boolean, default=True, nullable=False)
    notification_cooldown_minutes = Column(Integer, default=15, nullable=False)
    last_evaluated_at = Column(DateTime(timezone=True), nullable=True)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    project = relationship("Project", back_populates="alert_rules")
    events = relationship("AlertEvent", back_populates="rule", cascade="all, delete-orphan")


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String(36), ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="triggered", nullable=False)  # 'triggered', 'resolved'
    triggered_value = Column(Float, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    rule = relationship("AlertRule", back_populates="events")
    project = relationship("Project", back_populates="alert_events")

    __table_args__ = (
        Index("idx_alert_events_proj_time", "project_id", triggered_at.desc()),
        Index("idx_alert_events_active", "rule_id", "status"),
    )
