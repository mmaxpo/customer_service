from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContext,
)


class ObjectivePlanningStateKind(StrEnum):
    """
    Generic planner-facing classification of durable objective state.

    These values describe facts only. They are not planner commands
    and do not authorize candidate selection or execution.
    """

    NO_CONTEXT = "no_context"
    ABSENT = "absent"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    REPAIR_ACTIVE = "repair_active"
    REPAIR_TERMINAL = "repair_terminal"


class ObjectivePlanningStateSafety(BaseModel):
    """
    Hard boundary for Slice 6B1.

    The reasoner may classify durable facts but cannot itself alter
    ranking, select a capability, authorize execution, launch repair,
    or bypass approval and verification.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    informational_only: bool = True
    affects_ranking: bool = False
    affects_capability_selection: bool = False
    authorizes_execution: bool = False
    launches_repair: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False


class ObjectivePlanningState(BaseModel):
    """
    Immutable generic interpretation of one objective context.

    Product-specific repair planning remains owned by the registered
    ObjectiveRepairPlanner for the objective namespace and type.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    schema_version: str = "objective_planning_state.v1"

    kind: ObjectivePlanningStateKind

    objective_present: bool = False
    objective_terminal: bool = False
    objective_status: str | None = None

    unresolved_operation_count: int = Field(
        default=0,
        ge=0,
    )
    unresolved_operation_refs: tuple[str, ...] = ()

    repair_present: bool = False
    repair_status: str | None = None
    repair_disposition: str | None = None
    repair_attempt_number: int | None = Field(
        default=None,
        ge=1,
    )
    repair_terminal: bool = False

    human_approval_required: bool = False
    automatic_execution_allowed: bool = False

    reason_code: str
    summary: str

    safety: ObjectivePlanningStateSafety = Field(
        default_factory=ObjectivePlanningStateSafety
    )


class ObjectivePlanningStateReasoner:
    """
    Interpret durable objective facts for generic planner consumers.

    Responsibilities:
    - distinguish missing, absent, terminal, and unresolved objectives;
    - distinguish active and terminal durable repair attempts;
    - preserve unresolved target references and safety facts;
    - remain deterministic and product-neutral.

    Non-responsibilities:
    - no PlanCandidate creation;
    - no BusinessPlan creation;
    - no scoring or ordering;
    - no capability selection;
    - no repair planner invocation;
    - no workflow launch;
    - no execution authorization.
    """

    ACTIVE_REPAIR_STATUSES = frozenset(
        {
            "planned",
            "queued",
            "running",
            "paused",
        }
    )

    TERMINAL_REPAIR_STATUSES = frozenset(
        {
            "completed",
            "failed",
            "rejected",
        }
    )

    def reason(
        self,
        context: ObjectiveCognitiveContext | None,
    ) -> ObjectivePlanningState:
        if context is None:
            return ObjectivePlanningState(
                kind=(
                    ObjectivePlanningStateKind
                    .NO_CONTEXT
                ),
                reason_code="objective_context_not_supplied",
                summary=(
                    "No durable objective context was "
                    "supplied to planning."
                ),
            )

        if not context.present:
            return ObjectivePlanningState(
                kind=ObjectivePlanningStateKind.ABSENT,
                reason_code="objective_not_found",
                summary=(
                    "No durable objective resolution was "
                    "found in the requested scope."
                ),
            )

        resolution = context.resolution

        if resolution is None:
            raise ValueError(
                "Present objective context requires "
                "a resolution fact"
            )

        repair = context.latest_repair
        unresolved_refs = (
            resolution.unresolved_operation_refs
        )
        unresolved_count = (
            resolution.unresolved_operation_count
        )

        common = {
            "objective_present": True,
            "objective_terminal": (
                resolution.is_terminal
            ),
            "objective_status": resolution.status,
            "unresolved_operation_count": (
                unresolved_count
            ),
            "unresolved_operation_refs": (
                unresolved_refs
            ),
            "repair_present": repair is not None,
            "repair_status": (
                repair.status
                if repair is not None
                else None
            ),
            "repair_disposition": (
                repair.disposition
                if repair is not None
                else None
            ),
            "repair_attempt_number": (
                repair.attempt_number
                if repair is not None
                else None
            ),
            "human_approval_required": (
                repair.human_approval_required
                if repair is not None
                else False
            ),
            "automatic_execution_allowed": (
                repair.automatic_execution_allowed
                if repair is not None
                else False
            ),
        }

        if resolution.is_terminal:
            return ObjectivePlanningState(
                kind=(
                    ObjectivePlanningStateKind
                    .RESOLVED
                ),
                repair_terminal=(
                    self._repair_is_terminal(repair)
                ),
                reason_code="objective_resolution_terminal",
                summary=(
                    "The durable objective resolution is "
                    "terminal."
                ),
                **common,
            )

        if repair is not None:
            normalized_repair_status = (
                repair.status.strip().lower()
            )

            if (
                normalized_repair_status
                in self.ACTIVE_REPAIR_STATUSES
            ):
                return ObjectivePlanningState(
                    kind=(
                        ObjectivePlanningStateKind
                        .REPAIR_ACTIVE
                    ),
                    repair_terminal=False,
                    reason_code="objective_repair_active",
                    summary=(
                        "A durable repair attempt is "
                        "currently active."
                    ),
                    **common,
                )

            if (
                normalized_repair_status
                in self.TERMINAL_REPAIR_STATUSES
            ):
                return ObjectivePlanningState(
                    kind=(
                        ObjectivePlanningStateKind
                        .REPAIR_TERMINAL
                    ),
                    repair_terminal=True,
                    reason_code=(
                        "objective_repair_terminal"
                    ),
                    summary=(
                        "The latest durable repair attempt "
                        "is terminal while the objective "
                        "remains unresolved."
                    ),
                    **common,
                )

        return ObjectivePlanningState(
            kind=(
                ObjectivePlanningStateKind
                .UNRESOLVED
            ),
            repair_terminal=False,
            reason_code="objective_unresolved",
            summary=(
                "The durable objective remains unresolved "
                "and has no active or terminal repair "
                "classification."
            ),
            **common,
        )

    def _repair_is_terminal(
        self,
        repair,
    ) -> bool:
        if repair is None:
            return False

        return (
            repair.status.strip().lower()
            in self.TERMINAL_REPAIR_STATUSES
        )


__all__ = [
    "ObjectivePlanningState",
    "ObjectivePlanningStateKind",
    "ObjectivePlanningStateReasoner",
    "ObjectivePlanningStateSafety",
]
