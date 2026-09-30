from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowDefinitionCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class WorkflowVersionCreate(BaseModel):
    workflow_json: dict[str, Any]
    notes: str | None = None
    evaluation_summary: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinitionOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    slug: str
    description: str | None = None
    latest_version: int
    active_version: int | None = None
    metadata_json: dict[str, Any]


class WorkflowVersionOut(BaseModel):
    id: UUID
    workflow_definition_id: UUID
    user_id: UUID
    version: int
    workflow_json: dict[str, Any]
    status: str
    notes: str | None = None
    evaluation_summary: dict[str, Any]
    metadata_json: dict[str, Any]
