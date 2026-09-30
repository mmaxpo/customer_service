from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InboxTicketSummary(BaseModel):
    id: UUID
    status: str
    priority: str
    assigned_to: str | None = None


class InboxItem(BaseModel):
    conversation_id: UUID
    customer_id: UUID
    customer_name: str | None
    customer_email: str | None
    channel: str
    subject: str | None
    status: str
    latest_message: str | None
    created_at: datetime
    updated_at: datetime
    snoozed_until: datetime | None = None
    moderation_status: str = "normal"
    moderation_reason: str | None = None
    tags: list[str] = Field(default_factory=list)
    ticket: InboxTicketSummary | None = None

    model_config = {"from_attributes": True}
