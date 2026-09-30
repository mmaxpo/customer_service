from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContext,
)
from app.tcos.planner.runtime.objective_state_reasoner import (
    ObjectivePlanningState,
    ObjectivePlanningStateKind,
    ObjectivePlanningStateReasoner,
)


OBJECTIVE_REPAIR_DELEGATION_METRIC_KEY = (
    "objective_repair_delegation"
)

OBJECTIVE_REPAIR_DELEGATION_EVENT = (
    "ObjectiveRepairDelegationEvaluated"
)


class ObjectiveRepairDelegationKind(StrEnum):
    """
    Cognitive decision about product repair-planning delegation.

    These values describe a requested next responsibility. They do
    not invoke a product planner or authorize repair execution.
    """

    NO_DELEGATION = "no_delegation"
    REPAIR_PLANNING_REQUESTED = (
        "repair_planning_requested"
    )
    OBSERVE_EXISTING_REPAIR = (
        "observe_existing_repair"
    )
    SUBSEQUENT_REPAIR_PLANNING_REQUESTED = (
        "subsequent_repair_planning_requested"
    )


class ObjectiveRepairDelegationSafety(BaseModel):
    """
    Hard safety boundary for cognitive repair delegation.

    The decision may identify a next planning responsibility but
    cannot create or execute that work itself.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    informational_only: bool = True
    product_planning_required: bool = False

    persists_repair: bool = False
    publishes_event: bool = False
    enqueues_job: bool = False
    launches_workflow: bool = False
    authorizes_execution: bool = False

    bypasses_product_registry: bool = False
    bypasses_canonical_source_loading: bool = False
    bypasses_idempotency: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False


class ObjectiveRepairDelegationDecision(BaseModel):
    """
    Immutable cognitive projection of objective repair responsibility.

    A subsequent slice may consume a planning-request decision and
    delegate it through a product-composed repair planning service.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    schema_version: str = (
        "objective_repair_delegation.v1"
    )

    kind: ObjectiveRepairDelegationKind
    requested: bool = False

    objective_namespace: str | None = None
    objective_type: str | None = None
    objective_ref: str | None = None
    objective_version: int | None = Field(
        default=None,
        ge=1,
    )

    resolution_record_id: UUID | None = None
    repair_execution_id: UUID | None = None

    current_attempt_number: int | None = Field(
        default=None,
        ge=1,
    )
    requested_attempt_number: int | None = Field(
        default=None,
        ge=1,
    )

    objective_state: ObjectivePlanningState

    reason_code: str
    summary: str

    safety: ObjectiveRepairDelegationSafety

    @model_validator(mode="after")
    def validate_delegation(
        self,
    ) -> "ObjectiveRepairDelegationDecision":
        planning_kinds = {
            (
                ObjectiveRepairDelegationKind
                .REPAIR_PLANNING_REQUESTED
            ),
            (
                ObjectiveRepairDelegationKind
                .SUBSEQUENT_REPAIR_PLANNING_REQUESTED
            ),
        }

        should_request = self.kind in planning_kinds

        if self.requested != should_request:
            raise ValueError(
                "Delegation requested flag must match "
                "the delegation kind"
            )

        if (
            self.safety.product_planning_required
            != should_request
        ):
            raise ValueError(
                "Product planning requirement must match "
                "the delegation kind"
            )

        forbidden_safety = (
            self.safety.persists_repair,
            self.safety.publishes_event,
            self.safety.enqueues_job,
            self.safety.launches_workflow,
            self.safety.authorizes_execution,
            self.safety.bypasses_product_registry,
            (
                self.safety
                .bypasses_canonical_source_loading
            ),
            self.safety.bypasses_idempotency,
            self.safety.bypasses_approval,
            self.safety.bypasses_verification,
        )

        if any(forbidden_safety):
            raise ValueError(
                "Cognitive repair delegation cannot "
                "perform or bypass repair lifecycle work"
            )

        if should_request:
            required_identity = (
                self.objective_namespace,
                self.objective_type,
                self.objective_ref,
                self.objective_version,
                self.resolution_record_id,
                self.requested_attempt_number,
            )

            if any(
                value is None
                for value in required_identity
            ):
                raise ValueError(
                    "Repair planning delegation requires "
                    "complete durable objective identity"
                )

        if (
            self.kind
            == ObjectiveRepairDelegationKind
            .OBSERVE_EXISTING_REPAIR
            and self.repair_execution_id is None
        ):
            raise ValueError(
                "Existing-repair observation requires "
                "repair_execution_id"
            )

        return self


class ObjectiveRepairDelegationReasoner:
    """
    Convert durable objective state into a side-effect-free
    cognitive delegation decision.

    This reasoner never resolves a product planner and never calls
    ObjectiveRepairExecutionService.record_plan().
    """

    def reason(
        self,
        context: ObjectiveCognitiveContext | None,
    ) -> ObjectiveRepairDelegationDecision:
        state = (
            ObjectivePlanningStateReasoner()
            .reason(context)
        )

        if context is None:
            return self._no_delegation(
                state=state,
                reason_code="objective_context_not_supplied",
                summary=(
                    "No objective context was supplied, so "
                    "repair planning was not requested."
                ),
            )

        identity = context.identity
        resolution = context.resolution
        repair = context.latest_repair

        common = {
            "objective_namespace": (
                identity.namespace
            ),
            "objective_type": (
                identity.objective_type
            ),
            "objective_ref": (
                identity.objective_ref
            ),
            "objective_version": (
                identity.objective_version
            ),
            "resolution_record_id": (
                resolution.resolution_record_id
                if resolution is not None
                else None
            ),
            "repair_execution_id": (
                repair.repair_execution_id
                if repair is not None
                else None
            ),
            "current_attempt_number": (
                repair.attempt_number
                if repair is not None
                else None
            ),
            "objective_state": state,
        }

        if state.kind in {
            ObjectivePlanningStateKind.ABSENT,
            ObjectivePlanningStateKind.RESOLVED,
            ObjectivePlanningStateKind.NO_CONTEXT,
        }:
            return self._no_delegation(
                state=state,
                reason_code=(
                    "objective_does_not_require_repair"
                ),
                summary=(
                    "The durable objective state does not "
                    "require repair planning."
                ),
                **common,
            )

        if (
            state.kind
            == ObjectivePlanningStateKind
            .REPAIR_ACTIVE
        ):
            return ObjectiveRepairDelegationDecision(
                kind=(
                    ObjectiveRepairDelegationKind
                    .OBSERVE_EXISTING_REPAIR
                ),
                requested=False,
                requested_attempt_number=None,
                reason_code=(
                    "objective_repair_already_active"
                ),
                summary=(
                    "An existing durable repair attempt is "
                    "active and should be observed rather "
                    "than duplicated."
                ),
                safety=(
                    ObjectiveRepairDelegationSafety(
                        product_planning_required=False
                    )
                ),
                **common,
            )

        if (
            state.kind
            == ObjectivePlanningStateKind
            .REPAIR_TERMINAL
        ):
            if repair is None:
                raise ValueError(
                    "Terminal repair state requires a "
                    "durable repair fact"
                )

            return ObjectiveRepairDelegationDecision(
                kind=(
                    ObjectiveRepairDelegationKind
                    .SUBSEQUENT_REPAIR_PLANNING_REQUESTED
                ),
                requested=True,
                requested_attempt_number=(
                    repair.attempt_number + 1
                ),
                reason_code=(
                    "objective_unresolved_after_terminal_repair"
                ),
                summary=(
                    "The objective remains unresolved after "
                    "a terminal repair attempt, so another "
                    "product repair-planning attempt is "
                    "requested."
                ),
                safety=(
                    ObjectiveRepairDelegationSafety(
                        product_planning_required=True
                    )
                ),
                **common,
            )

        if (
            state.kind
            == ObjectivePlanningStateKind.UNRESOLVED
        ):
            return ObjectiveRepairDelegationDecision(
                kind=(
                    ObjectiveRepairDelegationKind
                    .REPAIR_PLANNING_REQUESTED
                ),
                requested=True,
                requested_attempt_number=1,
                reason_code=(
                    "objective_unresolved_without_repair"
                ),
                summary=(
                    "The durable objective remains unresolved "
                    "and has no classified repair attempt, so "
                    "product repair planning is requested."
                ),
                safety=(
                    ObjectiveRepairDelegationSafety(
                        product_planning_required=True
                    )
                ),
                **common,
            )

        raise ValueError(
            "Unsupported objective planning state: "
            f"{state.kind}"
        )

    @staticmethod
    def _no_delegation(
        *,
        state: ObjectivePlanningState,
        reason_code: str,
        summary: str,
        **identity,
    ) -> ObjectiveRepairDelegationDecision:
        supplied_state = identity.pop(
            "objective_state",
            None,
        )

        if (
            supplied_state is not None
            and supplied_state != state
        ):
            raise ValueError(
                "Delegation objective state mismatch"
            )

        return ObjectiveRepairDelegationDecision(
            kind=(
                ObjectiveRepairDelegationKind
                .NO_DELEGATION
            ),
            requested=False,
            objective_state=state,
            reason_code=reason_code,
            summary=summary,
            safety=ObjectiveRepairDelegationSafety(
                product_planning_required=False
            ),
            **identity,
        )


__all__ = [
    "OBJECTIVE_REPAIR_DELEGATION_EVENT",
    "OBJECTIVE_REPAIR_DELEGATION_METRIC_KEY",
    "ObjectiveRepairDelegationDecision",
    "ObjectiveRepairDelegationKind",
    "ObjectiveRepairDelegationReasoner",
    "ObjectiveRepairDelegationSafety",
]
