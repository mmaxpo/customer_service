from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    job_type: str
    payload: dict = Field(default_factory=dict)
    max_attempts: int = 3
    run_after: datetime | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None = None
    job_type: str
    status: str
    payload: dict
    result: dict | None = None
    error_message: str | None = None
    attempts: int
    max_attempts: int
    run_after: datetime | None = None
    locked_at: datetime | None = None
    locked_by: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
