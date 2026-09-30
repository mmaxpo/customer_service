from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversationDetailCustomer(BaseModel):
    id: UUID
    name: str | None
    email: str | None
    phone: str | None


class ConversationDetailMessage(BaseModel):
    id: UUID
    source_type: str | None = None
    source_message_id: UUID | None = None
    sender_type: str
    body: str
    meta: dict | None = None
    created_at: datetime


class ConversationDetailTicket(BaseModel):
    id: UUID
    title: str
    status: str
    priority: str
    assigned_to: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    id: UUID
    customer_id: UUID
    channel: str
    subject: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    customer: ConversationDetailCustomer | None
    messages: list[ConversationDetailMessage]
    ticket: ConversationDetailTicket | None
