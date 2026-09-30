from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CustomerActivityEventRead(BaseModel):
    type: str
    timestamp: datetime
    title: str
    description: str | None = None
    entity_id: UUID | None = None
    entity_type: str | None = None
    metadata: dict[str, Any] | None = None
