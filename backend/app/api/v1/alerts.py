from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_project_for_user
from app.db.session import get_db
from app.models.project import Project
from app.models.alert import AlertRule, AlertEvent
from app.schemas.alert import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertEventResponse,
)
from app.services.alert_evaluator import evaluate_single_rule

router = APIRouter(prefix="/projects/{project_id}/alerts", tags=["Alerts"])


@router.get("/rules", response_model=List[AlertRuleResponse])
def list_alert_rules(
    project: Project = Depends(get_project_for_user),
    db: Session = Depends(get_db),
):
    """List all alert rules configured for this project."""
    return db.query(AlertRule).filter(AlertRule.project_id == project.id).order_by(AlertRule.created_at.desc()).all()


@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
def create_alert_rule(
    rule_in: AlertRuleCreate,
    project: Project = Depends(get_project_for_user),
    db: Session = Depends(get_db),
):
    """Create a new threshold alert rule (e.g. error count > 20 in 5m or metric avg > threshold)."""
    if rule_in.rule_type == "metric_threshold" and not rule_in.target_metric:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_metric is required when rule_type is 'metric_threshold'",
        )

    rule = AlertRule(
        project_id=project.id,
        name=rule_in.name,
        rule_type=rule_in.rule_type,
        target_metric=rule_in.target_metric,
        condition_operator=rule_in.condition_operator,
        threshold=rule_in.threshold,
        window_minutes=rule_in.window_minutes,
        channel_type=rule_in.channel_type,
        channel_config=rule_in.channel_config,
        is_active=rule_in.is_active,
        notification_cooldown_minutes=rule_in.notification_cooldown_minutes,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
def update_alert_rule(
    rule_id: str,
    rule_in: AlertRuleUpdate,
    project: Project = Depends(get_project_for_user),
    db: Session = Depends(get_db),
):
    """Update an existing alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id, AlertRule.project_id == project.id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")

    update_data = rule_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert_rule(
    rule_id: str,
    project: Project = Depends(get_project_for_user),
    db: Session = Depends(get_db),
):
    """Delete an alert rule and cascade remove its events."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id, AlertRule.project_id == project.id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    db.delete(rule)
    db.commit()
    return None


@router.get("/events", response_model=List[AlertEventResponse])
def list_alert_events(
    project: Project = Depends(get_project_for_user),
    status_filter: Optional[str] = Query(None, description="Filter by status (triggered, resolved)"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List alert incident events for the project, sorted newest first."""
    query = db.query(AlertEvent).filter(AlertEvent.project_id == project.id)
    if status_filter:
        query = query.filter(AlertEvent.status == status_filter.lower())
    return query.order_by(AlertEvent.triggered_at.desc()).limit(limit).all()


@router.post("/evaluate")
def trigger_alert_evaluation(
    project: Project = Depends(get_project_for_user),
    db: Session = Depends(get_db),
):
    """Manually evaluate all active rules for this project immediately."""
    now = datetime.now(timezone.utc)
    rules = db.query(AlertRule).filter(AlertRule.project_id == project.id, AlertRule.is_active == True).all()
    evaluated_events = []
    for r in rules:
        ev = evaluate_single_rule(r, db, now)
        if ev:
            evaluated_events.append({
                "rule_id": r.id,
                "rule_name": r.name,
                "event_status": ev.status,
                "message": ev.message,
            })
    return {
        "status": "success",
        "rules_evaluated": len(rules),
        "events_affected": evaluated_events,
    }
