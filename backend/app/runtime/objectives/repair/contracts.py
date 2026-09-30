from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import (
    Any,
    Mapping,
    Protocol,
    runtime_checkable,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.runtime.objectives.resolution import (
    ObjectiveOperationStatus,
    ObjectiveReference,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionStatus,
)


class ObjectiveRepairDisposition(StrEnum):
    """
    Product-semantic continuation decision for an unresolved
    business objective.

    These values are intentionally separate from the
    existing plan-verification repair subsystem, which repairs
    invalid proposed plans rather than unresolved business
    outcomes.
    """

    RETRY_OPERATION = "retry_operation"
    WAIT_FOR_RESULT = "wait_for_result"
    REPLAN_REMAINING = "replan_remaining"
    REQUEST_HUMAN_ACTION = (
        "request_human_action"
    )
    STOP_REPAIR = "stop_repair"


class ObjectiveRepairSource(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    resolution_record_ref: str = Field(
        min_length=1,
    )

    objective: ObjectiveReference

    outcome_ref: str = Field(min_length=1)
    outcome_version: int = Field(ge=1)

    evaluation_ref: str = Field(min_length=1)
    evaluation_version: int = Field(ge=1)

    resolution_projection_version: int = Field(
        ge=1,
    )

    workflow_run_id: str | None = None

    @model_validator(mode="after")
    def normalize_identity(
        self,
    ) -> "ObjectiveRepairSource":
        self.resolution_record_ref = (
            self.resolution_record_ref.strip()
        )
        self.outcome_ref = self.outcome_ref.strip()
        self.evaluation_ref = (
            self.evaluation_ref.strip()
        )

        if self.workflow_run_id is not None:
            normalized_run_id = str(
                self.workflow_run_id
            ).strip()
            self.workflow_run_id = (
                normalized_run_id or None
            )

        if not self.resolution_record_ref:
            raise ValueError(
                "resolution record ref is required"
            )

        if not self.outcome_ref:
            raise ValueError(
                "outcome ref is required"
            )

        if not self.evaluation_ref:
            raise ValueError(
                "evaluation ref is required"
            )

        return self


class ObjectiveRepairTarget(BaseModel):
    """
    One required unresolved operation targeted by a repair
    request.

    operation_ref is scoped by the request's ObjectiveReference
    and must never be treated as globally unique.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    operation_ref: str = Field(min_length=1)
    operation_type: str = Field(min_length=1)

    resolution_status: ObjectiveOperationStatus
    required: bool = True

    reason_code: str | None = None
    summary: str | None = None

    source_task_id: str | None = None
    verification_ref: str | None = None

    evidence_refs: tuple[str, ...] = ()

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    @model_validator(mode="after")
    def validate_target(
        self,
    ) -> "ObjectiveRepairTarget":
        self.operation_ref = (
            self.operation_ref.strip()
        )
        self.operation_type = (
            self.operation_type.strip().lower()
        )

        if not self.operation_ref:
            raise ValueError(
                "repair target operation ref is required"
            )

        if not self.operation_type:
            raise ValueError(
                "repair target operation type is required"
            )

        if not self.required:
            raise ValueError(
                "repair target must be a required operation"
            )

        if self.resolution_status not in {
            ObjectiveOperationStatus.FAILED,
            ObjectiveOperationStatus.PENDING,
            ObjectiveOperationStatus.UNKNOWN,
        }:
            raise ValueError(
                "repair target must be failed, pending, "
                "or unknown"
            )

        if self.reason_code is not None:
            normalized_reason = (
                self.reason_code.strip().lower()
            )
            self.reason_code = (
                normalized_reason or None
            )

        if self.summary is not None:
            normalized_summary = self.summary.strip()
            self.summary = (
                normalized_summary or None
            )

        if self.source_task_id is not None:
            normalized_task_id = str(
                self.source_task_id
            ).strip()
            self.source_task_id = (
                normalized_task_id or None
            )

        if self.verification_ref is not None:
            normalized_verification_ref = str(
                self.verification_ref
            ).strip()
            self.verification_ref = (
                normalized_verification_ref
                or None
            )

        normalized_evidence_refs = tuple(
            value
            for value in (
                str(item).strip()
                for item in self.evidence_refs
            )
            if value
        )

        if len(normalized_evidence_refs) != len(
            set(normalized_evidence_refs)
        ):
            raise ValueError(
                "repair target evidence refs must be "
                "unique"
            )

        self.evidence_refs = (
            normalized_evidence_refs
        )

        return self


class ObjectiveRepairConstraints(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    allow_automatic_execution: bool = False
    require_human_approval: bool = False

    allowed_dispositions: tuple[
        ObjectiveRepairDisposition,
        ...,
    ]

    maximum_target_count: int | None = Field(
        default=None,
        ge=1,
    )

    not_before: datetime | None = None

    excluded_capability_ids: tuple[str, ...] = ()
    excluded_provider_refs: tuple[str, ...] = ()

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    @model_validator(mode="after")
    def validate_constraints(
        self,
    ) -> "ObjectiveRepairConstraints":
        if not self.allowed_dispositions:
            raise ValueError(
                "at least one repair disposition must "
                "be allowed"
            )

        if len(self.allowed_dispositions) != len(
            set(self.allowed_dispositions)
        ):
            raise ValueError(
                "allowed repair dispositions must be "
                "unique"
            )

        if (
            self.allow_automatic_execution
            and self.require_human_approval
        ):
            raise ValueError(
                "automatic execution and mandatory human "
                "approval cannot both be enabled"
            )

        if (
            self.not_before is not None
            and self.not_before.tzinfo is None
        ):
            raise ValueError(
                "not_before must be timezone-aware"
            )

        self.excluded_capability_ids = (
            self._normalize_unique_values(
                values=(
                    self.excluded_capability_ids
                ),
                field_name=(
                    "excluded capability ids"
                ),
                lowercase=True,
            )
        )

        self.excluded_provider_refs = (
            self._normalize_unique_values(
                values=(
                    self.excluded_provider_refs
                ),
                field_name=(
                    "excluded provider refs"
                ),
                lowercase=False,
            )
        )

        return self

    @staticmethod
    def _normalize_unique_values(
        *,
        values: tuple[str, ...],
        field_name: str,
        lowercase: bool,
    ) -> tuple[str, ...]:
        normalized = tuple(
            value.lower() if lowercase else value
            for value in (
                str(item).strip()
                for item in values
            )
            if value
        )

        if len(normalized) != len(
            set(normalized)
        ):
            raise ValueError(
                f"{field_name} must be unique"
            )

        return normalized


class ObjectiveRepairRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    schema_version: str = (
        "objective_repair_request.v1"
    )

    repair_request_ref: str = Field(
        min_length=1,
    )

    source: ObjectiveRepairSource

    resolution_status: ObjectiveResolutionStatus
    resolution_reason_code: str = Field(
        min_length=1,
    )
    resolution_summary: str = Field(
        min_length=1,
    )
    resolution_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    targets: tuple[
        ObjectiveRepairTarget,
        ...,
    ]

    constraints: ObjectiveRepairConstraints

    context: dict[str, Any] = Field(
        default_factory=dict,
    )

    @model_validator(mode="after")
    def validate_request(
        self,
    ) -> "ObjectiveRepairRequest":
        self.schema_version = (
            self.schema_version.strip()
        )
        self.repair_request_ref = (
            self.repair_request_ref.strip()
        )
        self.resolution_reason_code = (
            self.resolution_reason_code
            .strip()
            .lower()
        )
        self.resolution_summary = (
            self.resolution_summary.strip()
        )

        if not self.schema_version:
            raise ValueError(
                "repair request schema version is "
                "required"
            )

        if not self.repair_request_ref:
            raise ValueError(
                "repair request ref is required"
            )

        if not self.resolution_reason_code:
            raise ValueError(
                "resolution reason code is required"
            )

        if not self.resolution_summary:
            raise ValueError(
                "resolution summary is required"
            )

        if self.resolution_status in {
            ObjectiveResolutionStatus.ACHIEVED,
            (
                ObjectiveResolutionStatus
                .INTENTIONALLY_NOT_EXECUTED
            ),
        }:
            raise ValueError(
                "terminal resolved objective cannot "
                "produce a repair request"
            )

        if not self.targets:
            raise ValueError(
                "repair request requires at least one "
                "target"
            )

        target_refs = tuple(
            item.operation_ref
            for item in self.targets
        )

        if len(target_refs) != len(
            set(target_refs)
        ):
            raise ValueError(
                "repair target operation refs must be "
                "unique"
            )

        if (
            self.constraints.maximum_target_count
            is not None
            and len(self.targets)
            > self.constraints.maximum_target_count
        ):
            raise ValueError(
                "repair request exceeds maximum target "
                "count"
            )

        return self


class ObjectiveRepairAction(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    action_ref: str = Field(min_length=1)

    disposition: ObjectiveRepairDisposition

    target_operation_refs: tuple[str, ...]

    reason_code: str = Field(min_length=1)
    summary: str = Field(min_length=1)

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    automatic_execution_allowed: bool = False
    human_approval_required: bool = False

    wait_until: datetime | None = None
    wait_for_event_type: str | None = None

    planner_directives: dict[str, Any] = Field(
        default_factory=dict,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    @model_validator(mode="after")
    def validate_action(
        self,
    ) -> "ObjectiveRepairAction":
        self.action_ref = self.action_ref.strip()
        self.reason_code = (
            self.reason_code.strip().lower()
        )
        self.summary = self.summary.strip()

        if not self.action_ref:
            raise ValueError(
                "repair action ref is required"
            )

        if not self.reason_code:
            raise ValueError(
                "repair action reason code is required"
            )

        if not self.summary:
            raise ValueError(
                "repair action summary is required"
            )

        normalized_targets = tuple(
            value
            for value in (
                str(item).strip()
                for item in self.target_operation_refs
            )
            if value
        )

        if not normalized_targets:
            raise ValueError(
                "repair action requires at least one "
                "target"
            )

        if len(normalized_targets) != len(
            set(normalized_targets)
        ):
            raise ValueError(
                "repair action target refs must be "
                "unique"
            )

        self.target_operation_refs = (
            normalized_targets
        )

        if self.wait_for_event_type is not None:
            normalized_event_type = (
                self.wait_for_event_type.strip()
            )
            self.wait_for_event_type = (
                normalized_event_type or None
            )

        if (
            self.wait_until is not None
            and self.wait_until.tzinfo is None
        ):
            raise ValueError(
                "wait_until must be timezone-aware"
            )

        is_wait = (
            self.disposition
            == ObjectiveRepairDisposition
            .WAIT_FOR_RESULT
        )

        has_wait_instruction = (
            self.wait_until is not None
            or self.wait_for_event_type is not None
        )

        if is_wait and not has_wait_instruction:
            raise ValueError(
                "wait action requires wait_until or "
                "wait_for_event_type"
            )

        if (
            not is_wait
            and has_wait_instruction
        ):
            raise ValueError(
                "non-wait repair action cannot contain "
                "wait instructions"
            )

        if (
            self.disposition
            == ObjectiveRepairDisposition
            .REQUEST_HUMAN_ACTION
            and not self.human_approval_required
        ):
            raise ValueError(
                "human repair action must require human "
                "approval"
            )

        if (
            self.disposition
            in {
                ObjectiveRepairDisposition
                .REQUEST_HUMAN_ACTION,
                ObjectiveRepairDisposition
                .STOP_REPAIR,
            }
            and self.automatic_execution_allowed
        ):
            raise ValueError(
                "human or stop action cannot allow "
                "automatic execution"
            )

        return self


class ObjectiveRepairPlan(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    schema_version: str = (
        "objective_repair_plan.v1"
    )

    repair_request_ref: str = Field(
        min_length=1,
    )

    objective: ObjectiveReference

    disposition: ObjectiveRepairDisposition

    reason_code: str = Field(min_length=1)
    summary: str = Field(min_length=1)

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    actions: tuple[
        ObjectiveRepairAction,
        ...,
    ]

    planned_target_refs: tuple[str, ...]
    deferred_target_refs: tuple[str, ...] = ()
    unhandled_target_refs: tuple[str, ...] = ()

    automatic_execution_allowed: bool = False
    human_approval_required: bool = False

    planner_metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    @model_validator(mode="after")
    def validate_plan(
        self,
    ) -> "ObjectiveRepairPlan":
        self.schema_version = (
            self.schema_version.strip()
        )
        self.repair_request_ref = (
            self.repair_request_ref.strip()
        )
        self.reason_code = (
            self.reason_code.strip().lower()
        )
        self.summary = self.summary.strip()

        if not self.schema_version:
            raise ValueError(
                "repair plan schema version is required"
            )

        if not self.repair_request_ref:
            raise ValueError(
                "repair plan request ref is required"
            )

        if not self.reason_code:
            raise ValueError(
                "repair plan reason code is required"
            )

        if not self.summary:
            raise ValueError(
                "repair plan summary is required"
            )

        if not self.actions:
            raise ValueError(
                "repair plan requires at least one "
                "action"
            )

        action_refs = tuple(
            item.action_ref
            for item in self.actions
        )

        if len(action_refs) != len(
            set(action_refs)
        ):
            raise ValueError(
                "repair action refs must be unique"
            )

        self.planned_target_refs = (
            self._normalize_group(
                field_name="planned target refs",
                values=self.planned_target_refs,
            )
        )
        self.deferred_target_refs = (
            self._normalize_group(
                field_name="deferred target refs",
                values=self.deferred_target_refs,
            )
        )
        self.unhandled_target_refs = (
            self._normalize_group(
                field_name="unhandled target refs",
                values=self.unhandled_target_refs,
            )
        )

        planned = set(
            self.planned_target_refs
        )
        deferred = set(
            self.deferred_target_refs
        )
        unhandled = set(
            self.unhandled_target_refs
        )

        if (
            planned & deferred
            or planned & unhandled
            or deferred & unhandled
        ):
            raise ValueError(
                "repair target coverage groups must be "
                "disjoint"
            )

        action_target_refs = tuple(
            target_ref
            for action in self.actions
            for target_ref in (
                action.target_operation_refs
            )
        )

        if len(action_target_refs) != len(
            set(action_target_refs)
        ):
            raise ValueError(
                "repair target cannot appear in "
                "multiple actions"
            )

        if set(action_target_refs) != planned:
            raise ValueError(
                "repair action targets must exactly "
                "match planned_target_refs"
            )

        if (
            any(
                action.automatic_execution_allowed
                for action in self.actions
            )
            and not self.automatic_execution_allowed
        ):
            raise ValueError(
                "automatic repair action requires plan "
                "automatic execution permission"
            )

        if (
            any(
                action.human_approval_required
                for action in self.actions
            )
            and not self.human_approval_required
        ):
            raise ValueError(
                "human repair action requires plan "
                "human approval"
            )

        if (
            self.disposition
            == ObjectiveRepairDisposition
            .REQUEST_HUMAN_ACTION
            and not self.human_approval_required
        ):
            raise ValueError(
                "human repair plan must require human "
                "approval"
            )

        if (
            self.disposition
            == ObjectiveRepairDisposition
            .STOP_REPAIR
            and self.automatic_execution_allowed
        ):
            raise ValueError(
                "stop repair plan cannot allow "
                "automatic execution"
            )

        return self

    @staticmethod
    def _normalize_group(
        *,
        field_name: str,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        normalized = tuple(
            value
            for value in (
                str(item).strip()
                for item in values
            )
            if value
        )

        if len(normalized) != len(
            set(normalized)
        ):
            raise ValueError(
                f"{field_name} must be unique"
            )

        return normalized


@dataclass(frozen=True)
class ObjectiveRepairPlanningContext:
    request: ObjectiveRepairRequest
    resolution: ObjectiveResolutionAssessment

    prior_repair_plans: tuple[Any, ...] = ()

    product_context: (
        Mapping[str, Any] | None
    ) = None


@runtime_checkable
class ObjectiveRepairPlanner(Protocol):
    def plan_repair(
        self,
        context: ObjectiveRepairPlanningContext,
    ) -> ObjectiveRepairPlan:
        ...


__all__ = [
    "ObjectiveRepairAction",
    "ObjectiveRepairConstraints",
    "ObjectiveRepairDisposition",
    "ObjectiveRepairPlan",
    "ObjectiveRepairPlanner",
    "ObjectiveRepairPlanningContext",
    "ObjectiveRepairRequest",
    "ObjectiveRepairSource",
    "ObjectiveRepairTarget",
]
