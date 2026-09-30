from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    actor_id: UUID | None = None
    entity_type: str
    entity_id: UUID | None = None
    action: str
    message: str | None = None
    meta: dict | None = None
    created_at: datetime
