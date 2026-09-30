from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QueueCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    team_id: UUID | None = None
    channel: str | None = Field(default=None, max_length=64)
    intent: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, max_length=50)
    priority_rank: int = Field(default=100, ge=0, le=10000)
    is_default: bool = False
    is_active: bool = True
    filters: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


class QueueUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    team_id: UUID | None = None
    channel: str | None = Field(default=None, max_length=64)
    intent: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, max_length=50)
    priority_rank: int | None = Field(default=None, ge=0, le=10000)
    is_default: bool | None = None
    is_active: bool | None = None
    filters: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


class QueueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    team_id: UUID | None = None
    channel: str | None = None
    intent: str | None = None
    priority: str | None = None
    priority_rank: int
    is_default: bool
    is_active: bool
    filters: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
