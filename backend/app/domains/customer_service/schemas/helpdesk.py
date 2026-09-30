from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConversationSnoozeRequest(BaseModel):
    until: datetime
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def future_time(self):
        value = self.until
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
            self.until = value
        if value <= datetime.now(timezone.utc):
            raise ValueError("Snooze time must be in the future")
        return self


class ConversationModerationRequest(BaseModel):
    status: Literal["normal", "spam", "phishing", "quarantined"]
    reason: str | None = Field(default=None, max_length=500)


class BulkConversationActionRequest(BaseModel):
    conversation_ids: list[UUID] = Field(min_length=1, max_length=100)
    action: Literal["status", "assign", "tag", "snooze", "moderation"]
    value: str | None = Field(default=None, max_length=500)
    until: datetime | None = None


class ReplyDraftWrite(BaseModel):
    body: str = Field(min_length=1, max_length=100_000)
    source: Literal["agent", "ai", "autopilot"] = "agent"
    expected_version: int | None = Field(default=None, ge=1)


class ReplyDraftScheduleRequest(BaseModel):
    scheduled_for: datetime
    expected_version: int = Field(ge=1)


class ReplyDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    conversation_id: UUID
    author_user_id: UUID | None
    body: str
    status: str
    source: str
    version: int
    sent_message_id: UUID | None
    scheduled_for: datetime | None
    scheduled_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ReplySignatureWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=5_000)
    is_enabled: bool = True


class ReplySignatureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    scope_key: str
    user_id: UUID | None
    name: str
    body: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class CustomerCustomFieldsUpdate(BaseModel):
    custom_fields: dict[str, str | int | float | bool | None] = Field(max_length=100)
