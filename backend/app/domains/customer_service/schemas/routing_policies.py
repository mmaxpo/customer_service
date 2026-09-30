from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoutingPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    channel: str | None = Field(default=None, max_length=64)
    intent: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, max_length=50)

    strategy: str = Field(
        default="least_loaded", pattern="^(least_loaded|first_available)$"
    )
    candidate_assignee_ids: list[UUID] = Field(default_factory=list)
    candidate_team_ids: list[UUID] = Field(default_factory=list)
    candidate_queue_ids: list[UUID] = Field(default_factory=list)

    priority_rank: int = Field(default=100, ge=0, le=10000)
    is_fallback: bool = False
    is_active: bool = True
    filters: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


class RoutingPolicyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    channel: str | None = Field(default=None, max_length=64)
    intent: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, max_length=50)

    strategy: str | None = Field(
        default=None, pattern="^(least_loaded|first_available)$"
    )
    candidate_assignee_ids: list[UUID] | None = None
    candidate_team_ids: list[UUID] | None = None
    candidate_queue_ids: list[UUID] | None = None

    priority_rank: int | None = Field(default=None, ge=0, le=10000)
    is_fallback: bool | None = None
    is_active: bool | None = None
    filters: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


class RoutingPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    channel: str | None = None
    intent: str | None = None
    priority: str | None = None
    strategy: str
    candidate_assignee_ids: list
    candidate_team_ids: list
    candidate_queue_ids: list
    priority_rank: int
    is_fallback: bool
    is_active: bool
    filters: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
