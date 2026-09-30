from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domains.customer_service.models.enums import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    conversation_id: UUID
    title: str
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.NORMAL
    assigned_to: str | None = None


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assigned_to: str | None = None


class TicketRead(BaseModel):
    id: UUID
    user_id: UUID
    conversation_id: UUID
    title: str
    status: str
    priority: str
    assigned_to: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
