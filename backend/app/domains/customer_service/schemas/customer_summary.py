from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CustomerSummaryRead(BaseModel):
    customer_id: UUID

    name: str | None = None
    email: str | None = None

    conversation_count: int

    ticket_count: int
    open_ticket_count: int
    closed_ticket_count: int

    channels: list[str]

    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None

    latest_conversation_id: UUID | None = None
    latest_ticket_id: UUID | None = None
