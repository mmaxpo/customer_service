from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreateRequest(BaseModel):
    visitor_id: str
    channel: str = "website"
    customer_name: str | None = Field(default=None, max_length=255)
    customer_email: str | None = Field(default=None, max_length=320)


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    visitor_id: str
    channel: str
    status: str


class ChatMessageCreateRequest(BaseModel):
    content: str
    client_message_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime


class ChatConversationResponse(BaseModel):
    session_id: UUID
    messages: list[ChatMessageResponse]


class ChatWidgetSettingsUpdateRequest(BaseModel):
    enabled: bool | None = None
    title: str | None = Field(default=None, max_length=120)
    welcome_message: str | None = None
    brand_color: str | None = Field(default=None, max_length=32)
    position: str | None = Field(default=None, max_length=32)
    assistant_name: str | None = Field(default=None, max_length=120)
    auto_answer_enabled: bool | None = None
    auto_answer_confidence_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    human_handoff_enabled: bool | None = None
    human_handoff_message: str | None = None
    workflow_template_id: UUID | None = None
    meta: dict | None = None


class ChatWidgetSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    public_key: str
    enabled: bool
    title: str
    welcome_message: str
    brand_color: str
    position: str
    assistant_name: str
    auto_answer_enabled: bool
    auto_answer_confidence_threshold: float
    human_handoff_enabled: bool
    human_handoff_message: str
    workflow_template_id: UUID | None = None
    meta: dict | None = None


class PublicChatWidgetSettingsResponse(BaseModel):
    public_key: str
    enabled: bool
    title: str
    welcome_message: str
    brand_color: str
    position: str
    assistant_name: str
    auto_answer_enabled: bool
    auto_answer_confidence_threshold: float
    human_handoff_enabled: bool
    human_handoff_message: str
