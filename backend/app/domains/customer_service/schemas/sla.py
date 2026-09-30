from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SLAPolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    priority: str
    first_response_minutes: int = Field(gt=0)
    resolution_minutes: int = Field(gt=0)
    business_hours: dict | None = None
    calendar_id: UUID | None = None
    is_active: bool = True


class SLAPolicyRead(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    priority: str
    first_response_minutes: int
    resolution_minutes: int
    business_hours: dict | None = None
    calendar_id: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SLAViolationRead(BaseModel):
    id: UUID
    user_id: UUID
    ticket_id: UUID
    policy_id: UUID | None
    target_type: str
    due_at: datetime
    breached_at: datetime | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
