from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RealtimeEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: str
    scope: str
    user_id: UUID
    entity_type: str | None = None
    entity_id: UUID | str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
