from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventSubscriptionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    event_type: str = Field(..., min_length=1, max_length=255)
    channel: str | None = Field(default=None, max_length=64)

    workflow_template_id: UUID | None = None
    workflow_json: dict[str, Any] | None = None

    filters: dict[str, Any] | None = None
    is_active: bool = True
    meta: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_workflow_source(self):
        if self.workflow_template_id is None and self.workflow_json is None:
            raise ValueError("workflow_template_id or workflow_json is required")
        return self


class EventSubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    event_type: str
    channel: str | None = None
    workflow_template_id: UUID | None = None
    workflow_json: dict[str, Any] | None = None
    filters: dict[str, Any] | None = None
    is_active: bool
    meta: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class EventSubscriptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    event_type: str | None = Field(default=None, min_length=1, max_length=255)
    channel: str | None = Field(default=None, max_length=64)

    workflow_template_id: UUID | None = None
    workflow_json: dict[str, Any] | None = None

    filters: dict[str, Any] | None = None
    is_active: bool | None = None
    meta: dict[str, Any] | None = None


class SeedEventSubscriptionsRead(BaseModel):
    created: list[EventSubscriptionRead]
    existing: list[EventSubscriptionRead]
    created_count: int
    existing_count: int
