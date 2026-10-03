from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union, Literal
from pydantic import BaseModel, Field, field_validator
from app.core.config import settings

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def default_utcnow():
    return datetime.now(timezone.utc)


class LogIngestItem(BaseModel):
    level: LogLevel = "INFO"
    message: str = Field(..., min_length=1, max_length=settings.MAX_LOG_MESSAGE_LENGTH)
    timestamp: Optional[datetime] = None
    # Input field is called metadata (matching user SDK expectation), mapped internally
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("level", mode="before")
    def normalize_level(cls, v):
        if isinstance(v, str):
            v_upper = v.upper()
            if v_upper in ("DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"):
                if v_upper == "WARN":
                    return "WARNING"
                if v_upper == "FATAL":
                    return "CRITICAL"
                return v_upper
        return v


class MetricIngestItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    value: float = Field(...)
    timestamp: Optional[datetime] = None
    labels: Dict[str, Any] = Field(default_factory=dict)


# Ingestion request can be a single item or a list of items up to MAX_INGEST_BATCH_SIZE
class LogBatchIngest(BaseModel):
    items: List[LogIngestItem] = Field(..., max_length=settings.MAX_INGEST_BATCH_SIZE)


class MetricBatchIngest(BaseModel):
    items: List[MetricIngestItem] = Field(..., max_length=settings.MAX_INGEST_BATCH_SIZE)


class IngestResponse(BaseModel):
    status: str = "ok"
    ingested: int
