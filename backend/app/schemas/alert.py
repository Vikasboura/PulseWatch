from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict

RuleType = Literal["error_count", "metric_threshold"]
ConditionOperator = Literal[">", ">=", "<", "<="]
ChannelType = Literal["email", "slack"]
EventStatus = Literal["triggered", "resolved"]


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    rule_type: RuleType
    target_metric: Optional[str] = Field(None, max_length=100)
    condition_operator: ConditionOperator = ">"
    threshold: float
    window_minutes: int = Field(5, ge=1, le=1440)
    channel_type: ChannelType
    channel_config: Dict[str, Any] = Field(..., description="{'email': 'dev@...' or 'webhook_url': 'https://hooks.slack.com/...'}")
    is_active: bool = True
    notification_cooldown_minutes: int = Field(15, ge=1, le=1440)


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    target_metric: Optional[str] = None
    condition_operator: Optional[ConditionOperator] = None
    threshold: Optional[float] = None
    window_minutes: Optional[int] = Field(None, ge=1, le=1440)
    channel_type: Optional[ChannelType] = None
    channel_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    notification_cooldown_minutes: Optional[int] = Field(None, ge=1, le=1440)


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    rule_type: str
    target_metric: Optional[str] = None
    condition_operator: str
    threshold: float
    window_minutes: int
    channel_type: str
    channel_config: Dict[str, Any]
    is_active: bool
    notification_cooldown_minutes: int
    last_evaluated_at: Optional[datetime] = None
    last_notified_at: Optional[datetime] = None
    created_at: datetime


class AlertEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rule_id: str
    project_id: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    status: str
    triggered_value: float
    message: str
    created_at: datetime
