from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChannelConnectionCreate(BaseModel):
    channel: str = Field(..., min_length=1, max_length=64)
    external_account_id: str = Field(..., min_length=1, max_length=255)
    display_name: str | None = None
    config: dict[str, Any] | None = None


class ChannelConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    channel: str
    external_account_id: str
    display_name: str | None = None
    status: str
    config: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class OmnichannelInboundMedia(BaseModel):
    """Provider-neutral reference to inbound provider media.

    The provider adapter supplies references only. Product ingestion
    downloads, validates, scans, and persists the content later.
    """

    provider_media_id: str = Field(
        ...,
        min_length=1,
        max_length=512,
    )
    download_url: str | None = Field(
        default=None,
        max_length=4096,
    )
    filename: str | None = Field(
        default=None,
        max_length=255,
    )
    content_type: str | None = Field(
        default=None,
        max_length=255,
    )
    size_bytes: int | None = Field(
        default=None,
        ge=0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class OmnichannelOutboundAttachment(BaseModel):
    """Canonical product attachment selected for outbound delivery."""

    attachment_id: UUID


class OmnichannelInboundMessage(BaseModel):
    channel: str = Field(..., min_length=1, max_length=64)
    external_account_id: str = Field(..., min_length=1, max_length=255)
    external_thread_id: str = Field(..., min_length=1, max_length=255)
    external_message_id: str = Field(..., min_length=1, max_length=255)

    body: str = ""
    subject: str | None = None
    media: list[OmnichannelInboundMedia] = Field(
        default_factory=list,
    )

    external_customer_id: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None

    occurred_at: datetime | None = None
    raw_payload: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_body_or_media(self):
        if not self.body.strip() and not self.media:
            raise ValueError("Inbound message requires body or media")
        return self


class OmnichannelInboundResult(BaseModel):
    conversation_id: UUID
    message_id: UUID
    ticket_id: UUID | None = None
    customer_id: UUID
    channel: str
    duplicate: bool
    workflow: dict[str, Any] | None = None


class OmnichannelOutboundMessage(BaseModel):
    conversation_id: UUID
    body: str = ""
    sender_type: str = Field(
        default="agent",
        pattern="^(agent|ai|system)$",
    )
    external_thread_id: str | None = None
    idempotency_key: str | None = None
    attachments: list[OmnichannelOutboundAttachment] = Field(
        default_factory=list,
    )
    meta: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_body_or_attachments(self):
        if not self.body.strip() and not self.attachments:
            raise ValueError("Outbound message requires body or attachments")
        return self


class OmnichannelOutboundResult(BaseModel):
    conversation_id: UUID
    message_id: UUID
    external_message_id: str
    channel: str
    external_account_id: str
    external_thread_id: str
    delivery_status: str
    provider_response: dict[str, Any] | None = None


class OmnichannelDeliveryEvent(BaseModel):
    channel: str
    external_account_id: str
    external_message_id: str
    delivery_status: str
    event_id: str | None = None
    raw_payload: dict | None = None
    meta: dict | None = None


class OmnichannelDeliveryEventResult(BaseModel):
    external_message_id: str
    delivery_status: str
    updated: bool


class OmnichannelWebhookEventType(str, Enum):
    MESSAGE_INBOUND = "message_inbound"
    MESSAGE_DELIVERED = "message_delivered"
    MESSAGE_READ = "message_read"
    MESSAGE_FAILED = "message_failed"
    MESSAGE_TYPING = "message_typing"


class OmnichannelWebhookEvent(BaseModel):
    provider: str
    event_type: OmnichannelWebhookEventType

    channel: str

    external_account_id: str
    external_thread_id: str | None = None
    external_message_id: str | None = None
    external_customer_id: str | None = None

    body: str | None = None
    media: list[OmnichannelInboundMedia] = Field(
        default_factory=list,
    )

    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None

    delivery_status: str | None = None

    occurred_at: datetime | None = None

    raw_payload: dict | None = None
    meta: dict | None = None


class OmnichannelOutboundDeliveryJobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


class OmnichannelOutboundDeliveryJob(BaseModel):
    conversation_id: UUID
    message_id: UUID | None = None
    channel: str
    external_account_id: str
    external_thread_id: str
    body: str
    sender_type: str = "agent"
    attachment_ids: list[UUID] = Field(
        default_factory=list,
    )
    idempotency_key: str | None = None
    status: OmnichannelOutboundDeliveryJobStatus = (
        OmnichannelOutboundDeliveryJobStatus.QUEUED
    )
    attempts: int = 0
    meta: dict | None = None


class OmnichannelOutboundDeliveryJobEnqueueResult(BaseModel):
    job_id: UUID
    job_type: str
    status: str
    payload: dict
