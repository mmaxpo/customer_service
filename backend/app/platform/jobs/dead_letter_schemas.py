from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeadLetterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    user_id: UUID | None = None
    job_type: str
    payload: dict
    error_message: str
    attempts: int
    status: str
    created_at: datetime
