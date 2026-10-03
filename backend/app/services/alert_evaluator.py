"""
PulseWatch Alert Evaluator Service
-----------------------------------
Evaluates active alert rules across projects, records deduplicated incidents,
enforces notification cooldowns, and auto-resolves incidents when conditions clear.

BACKGROUND JOB HOSTING PLAN:
Background evaluation runs on a 60-second periodic loop inside the service process.
For production deployments, the host must keep a long-lived process alive:
  - Render / Railway: Standard web service dyno (runs continuously).
  - Cloud Run: Configure `min-instances: 1` and `cpu-allocation: always-on`
    so background asyncio tasks continue executing between incoming requests.
  - Or run a dedicated container command: `python -m app.services.alert_evaluator`
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.log_record import LogRecord
from app.models.metric_record import MetricRecord
from app.models.alert import AlertRule, AlertEvent
from app.services.notifier import dispatch_notification

logger = logging.getLogger(__name__)


def make_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def evaluate_condition(value: float, operator: str, threshold: float) -> bool:
    if operator == ">":
        return value > threshold
    elif operator == ">=":
        return value >= threshold
    elif operator == "<":
        return value < threshold
    elif operator == "<=":
        return value <= threshold
    return False


def evaluate_single_rule(rule: AlertRule, db: Session, now: datetime) -> Optional[AlertEvent]:
    window_start = now - timedelta(minutes=rule.window_minutes)
    current_value = 0.0

    if rule.rule_type == "error_count":
        # Count ERROR and CRITICAL logs within rolling window
        current_value = float(
            db.query(func.count(LogRecord.id))
            .filter(
                LogRecord.project_id == rule.project_id,
                LogRecord.level.in_(["ERROR", "CRITICAL"]),
                LogRecord.timestamp >= window_start,
                LogRecord.timestamp <= now,
            )
            .scalar() or 0.0
        )
        metric_label = f"error count ({rule.window_minutes}m window)"
    
    elif rule.rule_type == "metric_threshold":
        # Average value of metric within rolling window
        avg_val = (
            db.query(func.avg(MetricRecord.value))
            .filter(
                MetricRecord.project_id == rule.project_id,
                MetricRecord.name == rule.target_metric,
                MetricRecord.timestamp >= window_start,
                MetricRecord.timestamp <= now,
            )
            .scalar()
        )
        current_value = float(avg_val) if avg_val is not None else 0.0
        metric_label = f"{rule.target_metric} avg ({rule.window_minutes}m window)"
    
    else:
        logger.warning(f"Unrecognized rule type: {rule.rule_type}")
        return None

    rule.last_evaluated_at = now
    is_breached = evaluate_condition(current_value, rule.condition_operator, rule.threshold)

    # Check for an active (open) event for this rule
    active_event = (
        db.query(AlertEvent)
        .filter(AlertEvent.rule_id == rule.id, AlertEvent.status == "triggered")
        .first()
    )

    if is_breached:
        # Case 1: Condition breached and NO open event -> Create new event (Dedup)
        if not active_event:
            message = (
                f"Rule '{rule.name}' triggered: {metric_label} is {current_value} "
                f"({rule.condition_operator} threshold of {rule.threshold})."
            )
            new_event = AlertEvent(
                rule_id=rule.id,
                project_id=rule.project_id,
                triggered_at=now,
                status="triggered",
                triggered_value=current_value,
                message=message,
            )
            db.add(new_event)
            rule.last_notified_at = now
            db.commit()
            db.refresh(new_event)

            # Dispatch notification
            dispatch_notification(
                channel_type=rule.channel_type,
                channel_config=rule.channel_config,
                subject=f"ALERT TRIGGERED: {rule.name}",
                message=message,
                event_status="triggered",
            )
            
            # Broadcast over WebSocket if active
            _broadcast_alert_event(new_event)
            return new_event

        else:
            # Case 2: Already triggered -> Check notification cooldown
            cooldown_period = timedelta(minutes=rule.notification_cooldown_minutes)
            last_notif = make_aware(rule.last_notified_at)
            now_aware = make_aware(now)
            if not last_notif or (now_aware - last_notif >= cooldown_period):
                logger.info(f"Cooldown expired for rule '{rule.name}', re-sending notification.")
                rule.last_notified_at = now
                db.commit()
                dispatch_notification(
                    channel_type=rule.channel_type,
                    channel_config=rule.channel_config,
                    subject=f"ALERT STILL FIRING: {rule.name}",
                    message=f"Alert still active: {metric_label} is {current_value}.",
                    event_status="triggered",
                )
            return active_event

    else:
        # Case 3: Condition cleared and an active event was open -> Auto-resolve!
        if active_event:
            active_event.status = "resolved"
            active_event.resolved_at = now
            db.commit()
            db.refresh(active_event)

            resolve_message = (
                f"Rule '{rule.name}' resolved: {metric_label} dropped to {current_value} "
                f"(threshold was {rule.condition_operator} {rule.threshold})."
            )
            dispatch_notification(
                channel_type=rule.channel_type,
                channel_config=rule.channel_config,
                subject=f"RESOLVED: {rule.name}",
                message=resolve_message,
                event_status="resolved",
            )
            _broadcast_alert_event(active_event)
            return active_event

    db.commit()
    return None


def evaluate_all_rules(db: Session) -> int:
    """Evaluates all active rules across all projects."""
    now = datetime.now(timezone.utc)
    active_rules = db.query(AlertRule).filter(AlertRule.is_active == True).all()
    count = 0
    for rule in active_rules:
        try:
            evaluate_single_rule(rule, db, now)
            count += 1
        except Exception as e:
            logger.error(f"Error evaluating alert rule {rule.id}: {e}", exc_info=True)
    return count


def _broadcast_alert_event(event: AlertEvent):
    try:
        from app.api.v1.websockets import ws_manager
        ws_manager.broadcast_alert_sync(event.project_id, {
            "id": event.id,
            "rule_id": event.rule_id,
            "project_id": event.project_id,
            "status": event.status,
            "triggered_value": event.triggered_value,
            "message": event.message,
            "triggered_at": event.triggered_at.isoformat(),
            "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
        })
    except Exception:
        pass


async def alert_worker_loop(interval_seconds: int = 60):
    """Continuous background worker loop evaluating rules every minute."""
    logger.info("PulseWatch Alert Worker loop started.")
    while True:
        try:
            with SessionLocal() as db:
                evaluated = evaluate_all_rules(db)
                logger.debug(f"Alert worker evaluated {evaluated} active rules.")
        except Exception as e:
            logger.error(f"Unexpected error in alert worker loop: {e}", exc_info=True)
        await asyncio.sleep(interval_seconds)
