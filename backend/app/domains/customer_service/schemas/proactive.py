from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ProactiveSignal = Literal[
    "repeated_shipping_delays",
    "negative_csat",
    "vip_customer",
    "churn_chargeback_risk",
    "provider_outage",
    "repeated_failed_repairs",
]


class ProactiveAction(BaseModel):
    tag: bool = True
    set_priority: Literal["low", "normal", "high", "urgent"] | None = "urgent"
    notify_roles: list[Literal["owner", "admin", "agent"]] = Field(
        default_factory=lambda: ["owner", "admin"], max_length=3
    )


class ProactivePolicyWrite(BaseModel):
    signal: ProactiveSignal
    threshold: int = Field(default=1, ge=1, le=100)
    lookback_hours: int = Field(default=720, ge=1, le=8760)
    cooldown_hours: int = Field(default=24, ge=1, le=720)
    action: ProactiveAction = Field(default_factory=ProactiveAction)
    is_enabled: bool = True


class ProactivePolicyRead(ProactivePolicyWrite):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime


class ProactiveIncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    policy_id: UUID
    signal: str
    fingerprint: str
    severity: str
    status: str
    conversation_id: UUID | None
    customer_id: UUID | None
    provider_id: str | None
    evidence: dict
    action_taken: dict
    detected_at: datetime
    resolved_at: datetime | None
