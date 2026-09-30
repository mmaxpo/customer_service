from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SuggestedActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    action_type: str
    title: str
    description: str | None = None
    payload: dict | None = None
    confidence: float
    status: str
    source: str
    created_at: datetime


class ExecuteSuggestedActionRequest(BaseModel):
    payload: dict | None = None
