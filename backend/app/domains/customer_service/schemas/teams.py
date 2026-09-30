from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domains.customer_service.schemas.agents import AgentRead


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_active: bool = True
    meta: dict[str, Any] | None = None


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None
    meta: dict[str, Any] | None = None


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    is_active: bool
    meta: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class TeamMemberAdd(BaseModel):
    agent_id: UUID


class TeamMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    team_id: UUID
    agent_id: UUID
    created_at: datetime


class TeamDetail(TeamRead):
    members: list[AgentRead] = Field(default_factory=list)
