from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ArtifactKind(StrEnum):
    TEXT = "text"
    DOCUMENT = "document"
    JSON = "json"
    URL = "url"
    RESPONSE = "response"
    KNOWLEDGE = "knowledge"


class PlanningArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: ArtifactKind
    description: str = ""
    producer_task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    required: bool = True


class InvocationInput(BaseModel):
    artifact_id: str
    required: bool = True


class InvocationOutput(BaseModel):
    artifact_id: str
    kind: str = "generic"


class InvocationExecutionPolicy(BaseModel):
    timeout_ms: int | None = None
    retry_count: int = 0
    retry_backoff_ms: int = 0
    priority: int = 50


class PlanningCapabilityInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str
    arguments: dict[str, Any] = Field(default_factory=dict)

    inputs: list[InvocationInput] = Field(default_factory=list)
    outputs: list[InvocationOutput] = Field(default_factory=list)

    execution: InvocationExecutionPolicy = Field(
        default_factory=InvocationExecutionPolicy
    )

    metadata: dict[str, Any] = Field(default_factory=dict)

    # Backward-compatible fields while existing callers migrate.
    consumes: list[ArtifactReference] = Field(default_factory=list)
    produces: list[PlanningArtifact] = Field(default_factory=list)
    expected_artifact: str | None = None
    timeout_ms: int | None = None
    retry_count: int = Field(default=0, ge=0)

    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PlanningOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    business_task_id: str

    objective: str
    operation_type: str = "generic"

    selected_capability: str
    invocation: PlanningCapabilityInvocation | None = None
    candidate_capabilities: list[str] = Field(default_factory=list)

    consumes: list[ArtifactReference] = Field(default_factory=list)
    produces: list[PlanningArtifact] = Field(default_factory=list)

    reasoning: str = ""

    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def capability_id(self) -> str:
        # Backward-compatible name while compiler/tests migrate.
        return self.selected_capability


# Backward-compatible alias. New code should use PlanningOperation.
PlanningTask = PlanningOperation


class PlanningMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planner_version: str = "0.1"
    planning_strategy: str = "basic"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    extra: dict[str, Any] = Field(default_factory=dict)


class PlanningPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    business_plan_id: str

    operations: list[PlanningOperation] = Field(default_factory=list)
    artifacts: list[PlanningArtifact] = Field(default_factory=list)

    metadata: PlanningMetadata = Field(default_factory=PlanningMetadata)

    schema_version: str = "planning_ir.v1"

    @property
    def tasks(self) -> list[PlanningOperation]:
        # Backward-compatible name while callers migrate.
        return self.operations
