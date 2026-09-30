from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowDeploymentCreate(BaseModel):
    workflow_key: str
    workflow_version_id: UUID
    environment: str = "production"
    deployed_by: UUID | None = None
    metadata_json: dict = Field(default_factory=dict)


class WorkflowDeploymentRollbackRequest(BaseModel):
    target_workflow_version_id: UUID
    reason: str | None = None


class WorkflowDeploymentRead(BaseModel):
    id: UUID
    workflow_key: str
    workflow_version_id: UUID
    environment: str
    deployed_by: UUID | None = None
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime


class WorkflowDeploymentRollbackResult(BaseModel):
    rolled_back_from: UUID
    rolled_back_to: UUID
    reason: str | None = None
