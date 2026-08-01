from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class FeatureFlagOut(BaseModel):
    key: str
    value: str
    description: str

    model_config = {"from_attributes": True}


class FeatureFlagUpdate(BaseModel):
    value: str


class DashboardOut(BaseModel):
    active_sessions: int
    total_minutes_today: float
    total_users: int
    error_rate: float
    latency_p50_ms: int
    latency_p95_ms: int
    cost_today_usd: float


class AuditLogOut(BaseModel):
    id: UUID
    actor_id: str
    action: str
    resource: str
    detail: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ProviderKeyOut(BaseModel):
    provider: str
    is_active: bool
    priority: int
    health: str
    has_key: bool

    model_config = {"from_attributes": True}


class ProviderKeyUpsert(BaseModel):
    provider: str
    api_key: str
    priority: int = 100
    is_active: bool = True


class ForceEndRequest(BaseModel):
    reason: str = "admin_force_end"
