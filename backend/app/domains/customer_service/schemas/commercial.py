from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ReplySendRequest(BaseModel):
    body: str = Field(min_length=1, max_length=100_000)
    idempotency_key: str = Field(min_length=8, max_length=255)


class SavedViewCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    filters: dict[str, Any] = Field(default_factory=dict)
    is_shared: bool = False


class LeaseRequest(BaseModel):
    ttl_seconds: int = Field(default=90, ge=15, le=300)


class SLACalendarCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    timezone: str = "UTC"
    weekly_hours: dict[str, list[list[str]]] = Field(default_factory=dict)
    holidays: list[str] = Field(default_factory=list)
    escalation_policy: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class MergeRequest(BaseModel):
    source_id: UUID
    target_id: UUID


class ConversationSplitRequest(BaseModel):
    message_ids: list[UUID] = Field(min_length=1)
    subject: str | None = Field(default=None, max_length=255)


class ResolutionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=100)
    outcome: dict[str, Any] = Field(default_factory=dict)
    send_csat: bool = True


class CSATResponse(BaseModel):
    token: str = Field(min_length=32, max_length=255)
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=5000)


class OnboardingUpdate(BaseModel):
    checklist: dict[str, bool]


class CustomerConsentUpdate(BaseModel):
    marketing: bool | None = None
    support_processing: bool = True
    source: str = Field(default="merchant", min_length=1, max_length=64)


class SubscriptionUpdate(BaseModel):
    plan: Literal["trial", "starter", "growth", "pro"]
    status: Literal["trialing", "active", "past_due", "canceled", "paused"]
    entitlements: dict[str, Any] = Field(default_factory=dict)
    current_period_ends_at: datetime | None = None
    cancel_at_period_end: bool = False


class PrivacyRequestCreate(BaseModel):
    customer_id: UUID
    kind: Literal["export", "delete", "anonymize"]


class NotificationCreate(BaseModel):
    recipient_user_id: UUID
    kind: Literal["assignment", "mention", "handoff", "approval", "sla_risk"]
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ConversationFollowerRead(BaseModel):
    id: UUID
    conversation_id: UUID
    user_id: UUID
    followed_by_user_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
