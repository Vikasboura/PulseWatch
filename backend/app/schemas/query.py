from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class LogItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    project_id: str
    timestamp: datetime
    level: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="log_metadata")
    created_at: datetime


class LogListResponse(BaseModel):
    items: List[LogItemResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class MetricBucketPoint(BaseModel):
    bucket_time: datetime
    min: float
    max: float
    avg: float
    count: int


class MetricQueryResponse(BaseModel):
    metric_name: str
    bucket: str
    points: List[MetricBucketPoint]


class MetricNameItem(BaseModel):
    name: str
    count: int
    last_seen: datetime
