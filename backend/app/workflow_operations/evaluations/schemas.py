from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class WorkflowEvaluationCase(BaseModel):
    name: str
    workflow: dict[str, Any]
    message: str = ""
    expected_answer: Any | None = None
    expected_status: str | None = "ok"


class WorkflowEvaluationRequest(BaseModel):
    name: str = "workflow-evaluation"
    cases: list[WorkflowEvaluationCase] = Field(default_factory=list)


class WorkflowEvaluationCaseResult(BaseModel):
    name: str
    passed: bool
    score: float
    expected_answer: Any | None = None
    actual_answer: Any | None = None
    expected_status: str | None = None
    actual_status: str | None = None
    workflow_run_id: str | None = None
    job_id: str | None = None
    errors: list[str] = Field(default_factory=list)


class WorkflowEvaluationResult(BaseModel):
    name: str
    passed: bool
    score: float
    total_cases: int
    passed_cases: int
    failed_cases: int
    cases: list[WorkflowEvaluationCaseResult]


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
