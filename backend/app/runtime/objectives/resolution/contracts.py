from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping, Protocol, runtime_checkable

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class ObjectiveResolutionStatus(StrEnum):
    ACHIEVED = "achieved"
    PARTIALLY_ACHIEVED = "partially_achieved"
    PROGRESSING = "progressing"
    FAILED = "failed"
    INTENTIONALLY_NOT_EXECUTED = (
        "intentionally_not_executed"
    )
    INCONCLUSIVE = "inconclusive"


class ObjectiveOperationStatus(StrEnum):
    ACHIEVED = "achieved"
    FAILED = "failed"
    PENDING = "pending"
    UNKNOWN = "unknown"
    NOT_EXECUTED = "not_executed"


class ObjectiveReference(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    namespace: str = Field(min_length=1)
    objective_type: str = Field(min_length=1)
    objective_ref: str = Field(min_length=1)
    objective_version: int = Field(ge=1)

    @model_validator(mode="after")
    def normalize_identity(
        self,
    ) -> "ObjectiveReference":
        self.namespace = self.namespace.strip().lower()
        self.objective_type = (
            self.objective_type.strip().lower()
        )
        self.objective_ref = self.objective_ref.strip()

        if not self.namespace:
            raise ValueError(
                "objective namespace is required"
            )

        if not self.objective_type:
            raise ValueError(
                "objective type is required"
            )

        if not self.objective_ref:
            raise ValueError(
                "objective ref is required"
            )

        return self


class ObjectiveResolutionSource(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    outcome_ref: str = Field(min_length=1)
    outcome_version: int = Field(ge=1)

    evaluation_ref: str = Field(min_length=1)
    evaluation_version: int = Field(ge=1)

    workflow_run_id: str | None = None

    @model_validator(mode="after")
    def normalize_identity(
        self,
    ) -> "ObjectiveResolutionSource":
        self.outcome_ref = self.outcome_ref.strip()
        self.evaluation_ref = (
            self.evaluation_ref.strip()
        )

        if self.workflow_run_id is not None:
            normalized_run_id = (
                str(self.workflow_run_id).strip()
            )
            self.workflow_run_id = (
                normalized_run_id or None
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


class ObjectiveOperationResolution(BaseModel):
    """
    Resolution of one independently executable or
    independently verifiable objective operation.

    operation_ref is stable and unique within the owning
    ObjectiveReference. It is not required to be globally
    unique. Durable callers must identify an operation using
    the pair:

        (ObjectiveReference, operation_ref)
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    operation_ref: str = Field(min_length=1)
    operation_type: str = Field(min_length=1)

    status: ObjectiveOperationStatus
    required: bool = True

    reason_code: str | None = None
    summary: str | None = None

    source_task_id: str | None = None
    verification_ref: str | None = None

    evidence_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def normalize_identity(
        self,
    ) -> "ObjectiveOperationResolution":
        self.operation_ref = (
            self.operation_ref.strip()
        )
        self.operation_type = (
            self.operation_type.strip().lower()
        )

        if not self.operation_ref:
            raise ValueError(
                "operation ref is required"
            )

        if not self.operation_type:
            raise ValueError(
                "operation type is required"
            )

        normalized_evidence = tuple(
            value
            for value in (
                str(item).strip()
                for item in self.evidence_refs
            )
            if value
        )

        if len(normalized_evidence) != len(
            set(normalized_evidence)
        ):
            raise ValueError(
                "operation evidence refs must be unique"
            )

        self.evidence_refs = normalized_evidence
        return self


class ObjectiveResolutionAssessment(BaseModel):
    """
    Immutable-by-convention normalized assessment of one
    evaluated business objective.

    This contract describes business truth. It does not
    recommend, authorize, schedule, or execute repair.

    Operation references are interpreted within this
    assessment's ObjectiveReference. Repair and reverification
    must never treat operation_ref as a globally unique key.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    schema_version: str = (
        "objective_resolution.v1"
    )

    objective: ObjectiveReference
    source: ObjectiveResolutionSource

    status: ObjectiveResolutionStatus
    reason_code: str = Field(min_length=1)
    summary: str = Field(min_length=1)

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
    is_terminal: bool

    operations: tuple[
        ObjectiveOperationResolution,
        ...,
    ] = ()

    achieved_operation_refs: tuple[str, ...] = ()
    unresolved_operation_refs: tuple[str, ...] = ()
    failed_operation_refs: tuple[str, ...] = ()
    pending_operation_refs: tuple[str, ...] = ()
    unknown_operation_refs: tuple[str, ...] = ()
    not_executed_operation_refs: tuple[str, ...] = ()

    evidence_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def validate_assessment(
        self,
    ) -> "ObjectiveResolutionAssessment":
        self.reason_code = (
            self.reason_code.strip().lower()
        )
        self.summary = self.summary.strip()

        if not self.reason_code:
            raise ValueError(
                "resolution reason code is required"
            )

        if not self.summary:
            raise ValueError(
                "resolution summary is required"
            )

        operation_refs = tuple(
            item.operation_ref
            for item in self.operations
        )

        if len(operation_refs) != len(
            set(operation_refs)
        ):
            raise ValueError(
                "operation refs must be unique"
            )

        expected_achieved = tuple(
            item.operation_ref
            for item in self.operations
            if item.status
            == ObjectiveOperationStatus.ACHIEVED
        )
        expected_failed = tuple(
            item.operation_ref
            for item in self.operations
            if item.status
            == ObjectiveOperationStatus.FAILED
        )
        expected_pending = tuple(
            item.operation_ref
            for item in self.operations
            if item.status
            == ObjectiveOperationStatus.PENDING
        )
        expected_unknown = tuple(
            item.operation_ref
            for item in self.operations
            if item.status
            == ObjectiveOperationStatus.UNKNOWN
        )
        expected_not_executed = tuple(
            item.operation_ref
            for item in self.operations
            if item.status
            == ObjectiveOperationStatus.NOT_EXECUTED
        )

        expected_unresolved = tuple(
            item.operation_ref
            for item in self.operations
            if item.required
            and item.status
            in {
                ObjectiveOperationStatus.FAILED,
                ObjectiveOperationStatus.PENDING,
                ObjectiveOperationStatus.UNKNOWN,
            }
        )

        self._validate_or_assign_group(
            field_name="achieved_operation_refs",
            supplied=self.achieved_operation_refs,
            expected=expected_achieved,
        )
        self._validate_or_assign_group(
            field_name="failed_operation_refs",
            supplied=self.failed_operation_refs,
            expected=expected_failed,
        )
        self._validate_or_assign_group(
            field_name="pending_operation_refs",
            supplied=self.pending_operation_refs,
            expected=expected_pending,
        )
        self._validate_or_assign_group(
            field_name="unknown_operation_refs",
            supplied=self.unknown_operation_refs,
            expected=expected_unknown,
        )
        self._validate_or_assign_group(
            field_name=(
                "not_executed_operation_refs"
            ),
            supplied=(
                self.not_executed_operation_refs
            ),
            expected=expected_not_executed,
        )
        self._validate_or_assign_group(
            field_name=(
                "unresolved_operation_refs"
            ),
            supplied=(
                self.unresolved_operation_refs
            ),
            expected=expected_unresolved,
        )

        evidence_refs = tuple(
            value
            for value in (
                str(item).strip()
                for item in self.evidence_refs
            )
            if value
        )

        if len(evidence_refs) != len(
            set(evidence_refs)
        ):
            raise ValueError(
                "assessment evidence refs must be unique"
            )

        self.evidence_refs = evidence_refs

        if (
            self.status
            == ObjectiveResolutionStatus.ACHIEVED
        ):
            if not self.is_terminal:
                raise ValueError(
                    "achieved objective must be terminal"
                )

            if self.unresolved_operation_refs:
                raise ValueError(
                    "achieved objective cannot contain "
                    "unresolved operations"
                )

        if (
            self.status
            == ObjectiveResolutionStatus.PROGRESSING
            and self.is_terminal
        ):
            raise ValueError(
                "progressing objective cannot be terminal"
            )

        return self

    def _validate_or_assign_group(
        self,
        *,
        field_name: str,
        supplied: tuple[str, ...],
        expected: tuple[str, ...],
    ) -> None:
        normalized_supplied = tuple(
            value
            for value in (
                str(item).strip()
                for item in supplied
            )
            if value
        )

        if (
            normalized_supplied
            and normalized_supplied != expected
        ):
            raise ValueError(
                f"{field_name} does not match "
                "operation statuses"
            )

        setattr(
            self,
            field_name,
            expected,
        )


@dataclass(frozen=True)
class ObjectiveResolutionContext:
    objective: Any = None
    outcome: Any = None
    evaluation: Any = None
    metadata: Mapping[str, Any] | None = None


@runtime_checkable
class ObjectiveResolutionAdapter(Protocol):
    def assess(
        self,
        context: ObjectiveResolutionContext,
    ) -> ObjectiveResolutionAssessment:
        ...


__all__ = [
    "ObjectiveOperationResolution",
    "ObjectiveOperationStatus",
    "ObjectiveReference",
    "ObjectiveResolutionAdapter",
    "ObjectiveResolutionAssessment",
    "ObjectiveResolutionContext",
    "ObjectiveResolutionSource",
    "ObjectiveResolutionStatus",
]
