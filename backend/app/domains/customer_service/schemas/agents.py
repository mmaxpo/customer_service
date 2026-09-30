from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    agent_user_id: UUID
    display_name: str = Field(..., min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)

    status: str = Field(default="active", pattern="^(active|inactive)$")
    availability: str = Field(
        default="available", pattern="^(available|away|busy|offline)$"
    )
    availability_mode: str = Field(default="manual", pattern="^(manual|scheduled)$")
    schedule_timezone: str | None = None
    weekly_schedule: dict[str, list[dict[str, str]]] | None = None

    skills: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    max_open_tickets: int = Field(default=20, ge=1, le=1000)
    meta: dict[str, Any] | None = None


class AgentUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)

    status: str | None = Field(default=None, pattern="^(active|inactive)$")
    availability: str | None = Field(
        default=None, pattern="^(available|away|busy|offline)$"
    )
    availability_mode: str | None = Field(default=None, pattern="^(manual|scheduled)$")
    schedule_timezone: str | None = None
    weekly_schedule: dict[str, list[dict[str, str]]] | None = None

    skills: list[str] | None = None
    channels: list[str] | None = None
    languages: list[str] | None = None

    max_open_tickets: int | None = Field(default=None, ge=1, le=1000)
    meta: dict[str, Any] | None = None


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    agent_user_id: UUID
    display_name: str
    email: str | None = None
    status: str
    availability: str
    availability_source: str = "manual"
    availability_mode: str = "manual"
    schedule_timezone: str | None = None
    weekly_schedule: dict | None = None
    last_presence_at: datetime | None = None
    last_activity_at: datetime | None = None
    skills: list
    channels: list
    languages: list
    max_open_tickets: int
    meta: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class AgentPresenceUpdate(BaseModel):
    status: str = Field(pattern="^(available|away|busy|offline)$")


class AgentTimeOffCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=500)


class AgentTimeOffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workspace_id: UUID
    agent_id: UUID
    starts_at: datetime
    ends_at: datetime
    reason: str | None = None
    created_by_user_id: UUID | None = None
    created_at: datetime
