from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlatformEventCreate(BaseModel):
    event_type: str
    source: str = "platform"
    payload: dict = Field(default_factory=dict)
    meta: dict = Field(default_factory=dict)


class PlatformEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None = None
    event_type: str
    source: str
    payload: dict
    meta: dict
    status: str
    created_at: datetime
