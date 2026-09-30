from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConversationInsightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    conversation_id: UUID

    sentiment: str
    intent: str
    urgency: str

    summary: str
    root_cause: str | None = None

    entities: dict | None = None
    risks: dict | None = None
    opportunities: dict | None = None

    confidence: float | None = None
    source: str
    language: str = "und"
    model_version: str | None = None
    fallback_reason: str | None = None

    created_at: datetime
    updated_at: datetime


class ConversationInsightAnalyzeRequest(BaseModel):
    force_refresh: bool = False
