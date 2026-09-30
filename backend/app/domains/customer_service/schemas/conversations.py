from datetime import datetime
from uuid import UUID
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, model_validator


class ConversationCreate(BaseModel):
    customer_id: UUID
    channel: str = "email"
    subject: str | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    customer_id: UUID
    channel: str
    subject: str | None = None
    status: str
    meta: dict | None = None
    created_at: datetime
    updated_at: datetime


class SenderType(StrEnum):
    CUSTOMER = "customer"
    AGENT = "agent"
    AI = "ai"
    SYSTEM = "system"
    INTERNAL_NOTE = "internal_note"


class ConversationMessageCreate(BaseModel):
    sender_type: SenderType
    body: str
    meta: dict | None = None
    source_type: str | None = None
    source_message_id: UUID | None = None

    @model_validator(mode="after")
    def validate_source_identity(self):
        source_type = self.source_type.strip() if self.source_type is not None else None
        source_type = source_type or None

        if (source_type is None) != (self.source_message_id is None):
            raise ValueError(
                "source_type and source_message_id must be provided together"
            )

        self.source_type = source_type
        return self


class InternalNoteCreate(BaseModel):
    body: str
    meta: dict | None = None


class ConversationMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    source_type: str | None = None
    source_message_id: UUID | None = None
    sender_type: str
    body: str
    meta: dict | None = None
    created_at: datetime
