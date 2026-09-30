from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ConversationIntelligenceSnapshotRead(BaseModel):
    conversation_id: UUID
    intent: str | None = None
    urgency: str | None = None
    sentiment: str | None = None
    summary: str | None = None

    sla_risk: bool
    customer_risk_score: int | None = None
    customer_risk_level: str | None = None

    open_ticket: bool
    ticket_priority: str | None = None

    recommended_actions: list[str]
    tags: list[str]
    metadata: dict[str, Any]
