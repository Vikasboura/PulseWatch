from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    retention_days: int = Field(30, ge=1, le=365)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    retention_days: Optional[int] = Field(None, ge=1, le=365)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    retention_days: int
    created_at: datetime
    updated_at: datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_key: str  # Only returned upon creation
