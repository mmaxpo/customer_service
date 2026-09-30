from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkflowScheduleCreate(BaseModel):
    name: str
    workflow_id: UUID | None = None
    schedule_type: str = Field(pattern="^(once|interval|cron)$")
    interval_seconds: int | None = None
    cron_expression: str | None = None
    next_run_at: datetime
    timezone: str = "UTC"
    max_runs: int | None = None
    payload: dict = Field(default_factory=dict)


class WorkflowScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    workflow_id: UUID | None = None
    name: str
    schedule_type: str
    interval_seconds: int | None = None
    cron_expression: str | None = None
    timezone: str
    next_run_at: datetime
    last_run_at: datetime | None = None
    run_count: int
    max_runs: int | None = None
    status: str
    payload: dict
    created_at: datetime
