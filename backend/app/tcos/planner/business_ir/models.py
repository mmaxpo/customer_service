from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BusinessTaskCategory(StrEnum):
    INFORMATION = "information"
    DECISION = "decision"
    VALIDATION = "validation"
    ACTION = "action"
    COMMUNICATION = "communication"
    APPROVAL = "approval"
    VERIFICATION = "verification"


class BusinessDependencyType(StrEnum):
    HARD = "hard"
    SOFT = "soft"
    CONDITIONAL = "conditional"
    VERIFICATION = "verification"
    HUMAN = "human"


class BusinessConstraintSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    REQUIRED = "required"


class BusinessEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    name: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class CapabilityReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str
    version: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    alternatives: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BusinessConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    value: Any
    severity: BusinessConstraintSeverity = BusinessConstraintSeverity.MEDIUM
    required: bool = False
    reason: str | None = None


class BusinessVariable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source_task_id: str | None = None
    required: bool = False
    default: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BusinessTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""
    category: BusinessTaskCategory
    priority: int = Field(default=50, ge=0, le=100)
    required_capabilities: list[CapabilityReference] = Field(default_factory=list)
    inputs: list[BusinessVariable] = Field(default_factory=list)
    outputs: list[BusinessVariable] = Field(default_factory=list)
    estimated_duration_ms: int | None = Field(default=None, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)
    verification_requirements: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BusinessEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    target: str
    dependency_type: BusinessDependencyType = BusinessDependencyType.HARD
    condition: str | None = None
    priority: int = Field(default=50, ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BusinessGoal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str = ""
    priority: int = Field(default=50, ge=0, le=100)
    success_conditions: list[str] = Field(default_factory=list)
    entities: list[BusinessEntity] = Field(default_factory=list)
    constraints: list[BusinessConstraint] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BusinessDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str
    selected_option: str
    alternatives: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning_summary: str = ""


class BusinessPlanMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planner_version: str = "0.1"
    planning_strategy: str = "manual"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    estimated_cost: float | None = Field(default=None, ge=0)
    estimated_latency_ms: int | None = Field(default=None, ge=0)
    extra: dict[str, Any] = Field(default_factory=dict)


class BusinessPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    goal: BusinessGoal
    tasks: list[BusinessTask]
    edges: list[BusinessEdge] = Field(default_factory=list)
    variables: list[BusinessVariable] = Field(default_factory=list)
    constraints: list[BusinessConstraint] = Field(default_factory=list)
    decisions: list[BusinessDecision] = Field(default_factory=list)
    metadata: BusinessPlanMetadata = Field(default_factory=BusinessPlanMetadata)
    schema_version: str = "business_ir.v1"
