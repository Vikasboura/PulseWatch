from datetime import datetime, timezone
from typing import List, Union
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import insert

from app.api.deps import get_api_key_project
from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.db.session import get_db
from app.models.project import Project, ApiKey
from app.models.log_record import LogRecord
from app.models.metric_record import MetricRecord
from app.schemas.ingest import (
    LogIngestItem,
    MetricIngestItem,
    LogBatchIngest,
    MetricBatchIngest,
    IngestResponse,
)

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


def check_rate_limit(api_key: ApiKey):
    """Enforces sliding-window rate limit per API key."""
    allowed, current, remaining = rate_limiter.is_allowed(
        key_id=api_key.id,
        limit=settings.RATE_LIMIT_PER_MINUTE,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_PER_MINUTE} requests per minute allowed.",
            headers={"Retry-After": "60", "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE), "X-RateLimit-Remaining": "0"},
        )


@router.post("/logs", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_logs(
    payload: Union[LogBatchIngest, List[LogIngestItem], LogIngestItem],
    auth: tuple[Project, ApiKey] = Depends(get_api_key_project),
    db: Session = Depends(get_db),
):
    """
    Ingest logs authenticated by API key (X-API-Key header).
    Supports single items or batches up to 500 records.
    Uses bulk insertion for high throughput.
    """
    project, api_key = auth
    check_rate_limit(api_key)

    # Normalize payload into a list
    if isinstance(payload, LogBatchIngest):
        items = payload.items
    elif isinstance(payload, list):
        items = payload
    else:
        items = [payload]

    if len(items) > settings.MAX_INGEST_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size exceeds maximum limit of {settings.MAX_INGEST_BATCH_SIZE} items.",
        )

    if not items:
        return IngestResponse(status="ok", ingested=0)

    now = datetime.now(timezone.utc)
    records = []
    for item in items:
        ts = item.timestamp or now
        records.append({
            "project_id": project.id,
            "timestamp": ts,
            "level": item.level,
            "message": item.message,
            "log_metadata": item.metadata or {},
            "created_at": now,
        })

    # High-performance bulk insert
    db.execute(insert(LogRecord), records)
    db.commit()

    # Optional: trigger realtime websocket broadcast if broadcaster active
    try:
        from app.api.v1.websockets import ws_manager
        for r in records:
            ws_manager.broadcast_log_sync(project.id, {
                "project_id": r["project_id"],
                "timestamp": r["timestamp"].isoformat(),
                "level": r["level"],
                "message": r["message"],
                "metadata": r["log_metadata"],
            })
    except Exception:
        pass

    return IngestResponse(status="ok", ingested=len(records))


@router.post("/metrics", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_metrics(
    payload: Union[MetricBatchIngest, List[MetricIngestItem], MetricIngestItem],
    auth: tuple[Project, ApiKey] = Depends(get_api_key_project),
    db: Session = Depends(get_db),
):
    """
    Ingest time-series metrics authenticated by API key (X-API-Key header).
    Supports single points or batches up to 500 items.
    Uses bulk insertion for high throughput.
    """
    project, api_key = auth
    check_rate_limit(api_key)

    if isinstance(payload, MetricBatchIngest):
        items = payload.items
    elif isinstance(payload, list):
        items = payload
    else:
        items = [payload]

    if len(items) > settings.MAX_INGEST_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size exceeds maximum limit of {settings.MAX_INGEST_BATCH_SIZE} items.",
        )

    if not items:
        return IngestResponse(status="ok", ingested=0)

    now = datetime.now(timezone.utc)
    records = []
    for item in items:
        ts = item.timestamp or now
        records.append({
            "project_id": project.id,
            "name": item.name,
            "value": float(item.value),
            "timestamp": ts,
            "labels": item.labels or {},
            "created_at": now,
        })

    # High-performance bulk insert
    db.execute(insert(MetricRecord), records)
    db.commit()

    return IngestResponse(status="ok", ingested=len(records))
