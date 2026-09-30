from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class InboxEmailAddress(BaseModel):
    email: EmailStr
    name: str | None = None


class InboxAttachmentIn(BaseModel):
    filename: str
    content_type: str | None = None
    size_bytes: int | None = None
    url: str | None = None
    provider_attachment_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class NormalizedInboundEmail(BaseModel):
    provider: str
    external_account_id: str
    external_message_id: str
    external_thread_id: str | None = None

    from_address: InboxEmailAddress
    to: list[InboxEmailAddress] = Field(default_factory=list)
    cc: list[InboxEmailAddress] = Field(default_factory=list)
    bcc: list[InboxEmailAddress] = Field(default_factory=list)

    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None

    in_reply_to: str | None = None
    references: list[str] = Field(default_factory=list)

    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attachments: list[InboxAttachmentIn] = Field(default_factory=list)

    raw_payload: dict[str, Any] = Field(default_factory=dict)


class InboundEmailIngestResult(BaseModel):
    conversation_id: str
    message_id: str
    customer_email: str
    created_conversation: bool
    provider: str
    external_message_id: str
