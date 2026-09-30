from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowEvalCaseCreate(BaseModel):
    name: str
    input_payload: dict[str, Any]
    expected_output: dict[str, Any] = Field(default_factory=dict)
    expected_status: str | None = None
    tags: list[str] = Field(default_factory=list)
    priority: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class WorkflowEvalDatasetCreate(BaseModel):
    name: str
    description: str | None = None
    domain: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    cases: list[WorkflowEvalCaseCreate] = Field(default_factory=list)


class WorkflowEvalCaseRead(BaseModel):
    id: UUID
    dataset_id: UUID
    name: str
    input_payload: dict[str, Any]
    expected_output: dict[str, Any]
    expected_status: str | None
    tags: list[str]
    priority: str | None
    metadata_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowEvalDatasetRead(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str | None
    domain: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    cases: list[WorkflowEvalCaseRead]

    model_config = {"from_attributes": True}
