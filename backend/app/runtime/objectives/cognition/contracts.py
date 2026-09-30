from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class ObjectiveCognitiveReference(BaseModel):
    """
    Explicit caller-supplied reference to one durable objective.

    This contract never infers identity from natural-language
    input and does not itself contain durable objective facts.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    namespace: str = Field(
        min_length=1,
        max_length=255,
    )
    objective_ref: str = Field(
        min_length=1,
        max_length=500,
    )


class ObjectiveCognitiveIdentity(BaseModel):
    """
    Product-neutral durable objective identity.

    This contract identifies the objective whose current durable
    state is being exposed to cognition. It does not contain
    planner instructions.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    namespace: str = Field(
        min_length=1,
        max_length=255,
    )
    objective_ref: str = Field(
        min_length=1,
        max_length=500,
    )
    objective_type: str | None = Field(
        default=None,
        max_length=255,
    )
    objective_version: int | None = Field(
        default=None,
        ge=1,
    )


class ObjectiveResolutionCognitiveFact(BaseModel):
    """
    Normalized immutable view of the latest durable resolution.

    Only decision-relevant objective facts are included. The full
    assessment remains authoritative in ObjectiveResolutionRecord.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    resolution_record_id: UUID
    source_event_id: UUID

    tenant_id: str | None = None
    workflow_run_id: str | None = None

    status: str = Field(
        min_length=1,
        max_length=100,
    )
    reason_code: str = Field(
        min_length=1,
        max_length=255,
    )
    summary: str = Field(
        min_length=1,
        max_length=4000,
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
    is_terminal: bool

    source_outcome_ref: str = Field(
        min_length=1,
        max_length=500,
    )
    outcome_version: int = Field(ge=1)

    source_evaluation_ref: str = Field(
        min_length=1,
        max_length=500,
    )
    evaluation_version: int = Field(ge=1)
    projection_version: int = Field(ge=1)

    operation_count: int = Field(ge=0)
    achieved_operation_count: int = Field(ge=0)
    unresolved_operation_count: int = Field(ge=0)
    failed_operation_count: int = Field(ge=0)
    pending_operation_count: int = Field(ge=0)
    unknown_operation_count: int = Field(ge=0)
    not_executed_operation_count: int = Field(ge=0)

    unresolved_operation_refs: tuple[str, ...] = ()
    failed_operation_refs: tuple[str, ...] = ()
    pending_operation_refs: tuple[str, ...] = ()
    unknown_operation_refs: tuple[str, ...] = ()
    not_executed_operation_refs: tuple[str, ...] = ()

    created_at: datetime


class ObjectiveRepairCognitiveFact(BaseModel):
    """
    Normalized immutable view of the latest durable repair attempt.

    The repair service remains the source of truth for lifecycle
    transitions, workflow artifacts, and complete result payloads.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    repair_execution_id: UUID
    resolution_record_id: UUID
    source_event_id: UUID

    status: str = Field(
        min_length=1,
        max_length=100,
    )
    attempt_number: int = Field(ge=1)

    repair_request_ref: str = Field(
        min_length=1,
        max_length=500,
    )
    repair_request_version: int = Field(ge=1)

    planner_ref: str = Field(
        min_length=1,
        max_length=255,
    )
    planner_policy_version: int = Field(ge=1)

    disposition: str = Field(
        min_length=1,
        max_length=100,
    )
    reason_code: str = Field(
        min_length=1,
        max_length=255,
    )
    summary: str = Field(
        min_length=1,
        max_length=4000,
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    automatic_execution_allowed: bool
    human_approval_required: bool

    workflow_job_id: UUID | None = None
    workflow_run_id: str | None = None

    runtime_status: str | None = None
    repair_result_status: str | None = None

    failure_code: str | None = None
    failure_message: str | None = None

    created_at: datetime
    completed_at: datetime | None = None


class ObjectiveCognitiveSafety(BaseModel):
    """
    Hard safety boundary for durable cognitive context.

    Slice 6A1 only exposes facts. It cannot alter planning,
    authorize execution, or bypass runtime controls.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    informational_only: bool = True
    affects_ranking: bool = False
    affects_capability_selection: bool = False
    authorizes_execution: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False

    @model_validator(mode="after")
    def validate_boundary(self):
        if not self.informational_only:
            raise ValueError(
                "Objective cognitive context must remain "
                "informational in Slice 6A1"
            )

        if any(
            (
                self.affects_ranking,
                self.affects_capability_selection,
                self.authorizes_execution,
                self.bypasses_approval,
                self.bypasses_verification,
            )
        ):
            raise ValueError(
                "Objective cognitive context cannot alter "
                "planning or execution decisions"
            )

        return self


class ObjectiveCognitiveProvenance(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    source: str = (
        "durable_objective_records"
    )
    resolution_record_id: UUID | None = None
    repair_execution_id: UUID | None = None


class ObjectiveCognitiveContext(BaseModel):
    """
    Read-only normalized context for one durable objective.

    Absence is represented explicitly. Consumers must not infer
    success, failure, or repair state when `present` is false.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    schema_version: str = (
        "objective_cognitive_context.v1"
    )

    present: bool
    identity: ObjectiveCognitiveIdentity

    resolution: (
        ObjectiveResolutionCognitiveFact | None
    ) = None
    latest_repair: (
        ObjectiveRepairCognitiveFact | None
    ) = None

    provenance: ObjectiveCognitiveProvenance
    safety: ObjectiveCognitiveSafety = Field(
        default_factory=ObjectiveCognitiveSafety
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def validate_presence(self):
        if self.present and self.resolution is None:
            raise ValueError(
                "Present objective cognitive context "
                "requires a resolution"
            )

        if not self.present and (
            self.resolution is not None
            or self.latest_repair is not None
        ):
            raise ValueError(
                "Absent objective cognitive context "
                "cannot contain durable facts"
            )

        if (
            self.latest_repair is not None
            and self.resolution is not None
            and self.latest_repair.resolution_record_id
            != self.resolution.resolution_record_id
        ):
            raise ValueError(
                "Repair fact must belong to the "
                "selected resolution"
            )

        return self


__all__ = [
    "ObjectiveCognitiveContext",
    "ObjectiveCognitiveIdentity",
    "ObjectiveCognitiveProvenance",
    "ObjectiveCognitiveReference",
    "ObjectiveCognitiveSafety",
    "ObjectiveRepairCognitiveFact",
    "ObjectiveResolutionCognitiveFact",
]
