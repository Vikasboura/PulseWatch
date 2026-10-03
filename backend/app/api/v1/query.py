from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.api.deps import get_project_for_user
from app.db.session import get_db
from app.models.project import Project
from app.models.log_record import LogRecord
from app.models.metric_record import MetricRecord
from app.schemas.query import (
    LogListResponse,
    LogItemResponse,
    MetricQueryResponse,
    MetricBucketPoint,
    MetricNameItem,
)
from app.services.retention import purge_expired_records

router = APIRouter(prefix="/projects/{project_id}", tags=["Queries"])


@router.get("/logs", response_model=LogListResponse)
def get_logs(
    project: Project = Depends(get_project_for_user),
    level: Optional[str] = Query(None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    search: Optional[str] = Query(None, description="Search keyword in log message"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp (UTC)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp (UTC)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    db: Session = Depends(get_db),
):
    """
    Query logs with multi-field filtering, full-text search, and pagination.
    Uses indexed queries on project_id, level, and timestamp.
    """
    query = db.query(LogRecord).filter(LogRecord.project_id == project.id)

    if level:
        query = query.filter(LogRecord.level == level.upper())
    if start_time:
        query = query.filter(LogRecord.timestamp >= start_time)
    if end_time:
        query = query.filter(LogRecord.timestamp <= end_time)
    if search:
        query = query.filter(LogRecord.message.ilike(f"%{search.strip()}%"))

    total = query.count()
    offset = (page - 1) * limit

    items = query.order_by(LogRecord.timestamp.desc()).offset(offset).limit(limit).all()
    has_more = (offset + len(items)) < total

    formatted_items = [
        LogItemResponse(
            id=item.id,
            project_id=item.project_id,
            timestamp=item.timestamp,
            level=item.level,
            message=item.message,
            metadata=item.log_metadata or {},
            created_at=item.created_at,
        )
        for item in items
    ]

    return LogListResponse(
        items=formatted_items,
        total=total,
        page=page,
        limit=limit,
        has_more=has_more,
    )


@router.get("/metrics/names", response_model=List[MetricNameItem])
def get_metric_names(
    project: Project = Depends(get_project_for_user),
    db: Session = Depends(get_db),
):
    """List distinct metric names recorded for this project."""
    rows = (
        db.query(
            MetricRecord.name,
            func.count(MetricRecord.id).label("count"),
            func.max(MetricRecord.timestamp).label("last_seen"),
        )
        .filter(MetricRecord.project_id == project.id)
        .group_by(MetricRecord.name)
        .order_by(desc("count"))
        .all()
    )
    return [
        MetricNameItem(name=r.name, count=r.count, last_seen=r.last_seen)
        for r in rows
    ]


@router.get("/metrics", response_model=MetricQueryResponse)
def get_metrics_aggregated(
    project: Project = Depends(get_project_for_user),
    name: str = Query(..., description="Metric name to query"),
    start_time: Optional[datetime] = Query(None, description="Start time (UTC). Defaults to 1 hour ago"),
    end_time: Optional[datetime] = Query(None, description="End time (UTC). Defaults to now"),
    bucket: str = Query("5m", pattern="^(1m|5m|1h|raw)$", description="Aggregation bucket window"),
    db: Session = Depends(get_db),
):
    """
    Query metrics aggregated into time buckets (1m, 5m, 1h) or raw.
    Computes min, max, avg, and count per time bucket.
    Compatible across SQLite and PostgreSQL.
    """
    now = datetime.now(timezone.utc)
    if not end_time:
        end_time = now
    if not start_time:
        start_time = end_time - timedelta(hours=1)

    # Fetch raw points ordered chronologically
    records = (
        db.query(MetricRecord)
        .filter(
            MetricRecord.project_id == project.id,
            MetricRecord.name == name,
            MetricRecord.timestamp >= start_time,
            MetricRecord.timestamp <= end_time,
        )
        .order_by(MetricRecord.timestamp.asc())
        .all()
    )

    if bucket == "raw" or not records:
        points = [
            MetricBucketPoint(
                bucket_time=r.timestamp,
                min=r.value,
                max=r.value,
                avg=r.value,
                count=1,
            )
            for r in records
        ]
        return MetricQueryResponse(metric_name=name, bucket=bucket, points=points)

    # Bucket resolution in seconds
    bucket_seconds = 60 if bucket == "1m" else (300 if bucket == "5m" else 3600)

    # Group into time buckets
    buckets: dict[int, list[float]] = {}
    for r in records:
        ts_epoch = int(r.timestamp.timestamp())
        bucket_key = (ts_epoch // bucket_seconds) * bucket_seconds
        if bucket_key not in buckets:
            buckets[bucket_key] = []
        buckets[bucket_key].append(r.value)

    points = []
    for b_epoch in sorted(buckets.keys()):
        vals = buckets[b_epoch]
        b_time = datetime.fromtimestamp(b_epoch, tz=timezone.utc)
        points.append(
            MetricBucketPoint(
                bucket_time=b_time,
                min=round(min(vals), 4),
                max=round(max(vals), 4),
                avg=round(sum(vals) / len(vals), 4),
                count=len(vals),
            )
        )

    return MetricQueryResponse(metric_name=name, bucket=bucket, points=points)


@router.post("/retention/purge")
def trigger_retention_purge(
    project: Project = Depends(get_project_for_user),
    db: Session = Depends(get_db),
):
    """Manually trigger data retention cleanup for this project."""
    res = purge_expired_records(db, project_id=project.id)
    return {
        "status": "success",
        "detail": f"Purged {res['logs_purged']} logs and {res['metrics_purged']} metrics older than {project.retention_days} days.",
        **res,
    }
