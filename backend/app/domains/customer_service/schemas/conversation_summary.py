from __future__ import annotations

from pydantic import BaseModel, Field


class ConversationSummaryRead(BaseModel):
    summary: str
    intent: str | None = None
    sentiment: str | None = None
    urgency: str | None = None
    entities: dict = Field(default_factory=dict)
