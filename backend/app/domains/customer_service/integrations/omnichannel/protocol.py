from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class OmnichannelDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class OmnichannelDeliveryStatus(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class OmnichannelProviderConnectionContext(BaseModel):
    """Provider-neutral execution context for one channel connection.

    Product/domain orchestration may load persistence models, but adapters
    receive only this detached DTO. Provider-specific config remains opaque
    outside the adapter.
    """

    channel: str = Field(..., min_length=1, max_length=64)
    external_account_id: str = Field(..., min_length=1, max_length=255)
    config: dict[str, Any] = Field(default_factory=dict)


class FetchedInboundMedia(BaseModel):
    """Provider-fetched binary media ready for canonical product validation."""

    content: bytes
    filename: str | None = None
    content_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedInboundMedia(BaseModel):
    """Provider-normalized inbound media reference.

    Provider-specific IDs stay at this boundary and are not the
    canonical Customer Service attachment identity.
    """

    provider_media_id: str = Field(
        ...,
        min_length=1,
        max_length=512,
    )
    download_url: str | None = None
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = Field(
        default=None,
        ge=0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class NormalizedOutboundAttachment(BaseModel):
    """Canonical attachment prepared for a provider adapter."""

    attachment_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class NormalizedInboundMessage(BaseModel):
    channel: str = Field(..., min_length=1, max_length=64)
    external_account_id: str = Field(..., min_length=1, max_length=255)
    external_thread_id: str = Field(..., min_length=1, max_length=255)
    external_message_id: str = Field(..., min_length=1, max_length=255)
    body: str = ""
    subject: str | None = None
    external_customer_id: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    occurred_at: datetime | None = None
    media: list[NormalizedInboundMedia] = Field(
        default_factory=list,
    )
    raw_payload: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_body_or_media(self):
        if not self.body.strip() and not self.media:
            raise ValueError("Normalized inbound message requires body or media")
        return self


class NormalizedOutboundMessage(BaseModel):
    user_id: UUID
    conversation_id: UUID
    channel: str = Field(..., min_length=1, max_length=64)
    external_account_id: str = Field(..., min_length=1, max_length=255)
    external_thread_id: str = Field(..., min_length=1, max_length=255)
    body: str = ""
    sender_type: str = "agent"
    attachments: list[NormalizedOutboundAttachment] = Field(
        default_factory=list,
    )
    idempotency_key: str | None = None
    meta: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_body_or_attachments(self):
        if not self.body.strip() and not self.attachments:
            raise ValueError("Normalized outbound message requires body or attachments")
        return self


class NormalizedOutboundResult(BaseModel):
    external_message_id: str
    delivery_status: OmnichannelDeliveryStatus = OmnichannelDeliveryStatus.SENT
    raw_response: dict[str, Any] | None = None


class NormalizedDeliveryEvent(BaseModel):
    channel: str = Field(..., min_length=1, max_length=64)
    external_account_id: str = Field(..., min_length=1, max_length=255)
    external_message_id: str = Field(..., min_length=1, max_length=255)
    delivery_status: OmnichannelDeliveryStatus
    occurred_at: datetime | None = None
    raw_payload: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


class WebhookVerificationResult(BaseModel):
    verified: bool
    reason: str | None = None


class OmnichannelProviderVerificationProtocol:
    async def verify_webhook_signature(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> WebhookVerificationResult: ...


class OmnichannelProviderCapabilities(BaseModel):
    channel: str
    production_ready: bool = False
    supports_inbound: bool = True
    supports_outbound: bool = True
    supports_delivery_receipts: bool = True
    supports_read_receipts: bool = False
    supports_typing_indicators: bool = False
    supports_attachments: bool = False
    supports_templates: bool = False
