from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkflowWaitCreate(BaseModel):
    workflow_run_id: str
    node_id: str | None = None
    wait_type: str = Field(pattern="^(approval|time|webhook|event|external)$")
    payload: dict = Field(default_factory=dict)
    expires_at: datetime | None = None


class WorkflowWaitResolve(BaseModel):
    resolution: dict = Field(default_factory=dict)
    resume: bool = True


class WorkflowWaitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    workflow_run_id: str
    node_id: str | None = None
    wait_type: str
    status: str
    payload: dict
    resolution: dict | None = None
    expires_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime
