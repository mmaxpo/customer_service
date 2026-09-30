from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationTagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ConversationTagRead(BaseModel):
    id: UUID
    user_id: UUID
    conversation_id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
