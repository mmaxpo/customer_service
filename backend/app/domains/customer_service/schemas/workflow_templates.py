from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class WorkflowTemplateCreate(BaseModel):
    category: str

    name: str

    description: str | None = None

    workflow_json: dict

    input_schema: dict | None = None

    output_schema: dict | None = None

    tags: list[str] | None = None


class WorkflowTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    category: str

    name: str

    description: str | None = None

    workflow_json: dict

    tags: list | None = None

    scope: str

    version: str

    status: str

    created_at: datetime


class SeedWorkflowTemplatesRead(BaseModel):
    created: list[WorkflowTemplateRead]

    existing: list[WorkflowTemplateRead]

    created_count: int

    existing_count: int


class WorkflowTemplateCloneRequest(BaseModel):
    name: str | None = None

    description: str | None = None


class WorkflowTemplateUpdate(BaseModel):
    category: str | None = None

    name: str | None = None

    description: str | None = None

    workflow_json: dict | None = None

    input_schema: dict | None = None

    output_schema: dict | None = None

    tags: list[str] | None = None
