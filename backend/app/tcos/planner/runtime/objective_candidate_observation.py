from __future__ import annotations

from copy import deepcopy

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.tcos.planner.runtime.objective_state_reasoner import (
    ObjectivePlanningState,
    ObjectivePlanningStateKind,
    ObjectivePlanningStateReasoner,
)
from app.tcos.planner.runtime.plan_candidate import (
    PlanCandidate,
)
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)


OBJECTIVE_STATE_OBSERVATION_KEY = (
    "durable_objective_state_observation"
)


class ObjectiveCandidateObservation(BaseModel):
    """
    Read-only durable-objective observation attached to a candidate.

    This contract records objective state visible during planning.
    It cannot alter candidate scoring, ordering, capability selection,
    BusinessPlan content, approval, verification, repair, compilation,
    or execution.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    available: bool = False
    objective_present: bool = False

    state_kind: ObjectivePlanningStateKind = (
        ObjectivePlanningStateKind.NO_CONTEXT
    )
    state: ObjectivePlanningState

    informational_only: bool = True
    affects_score: bool = False
    affects_ordering: bool = False
    affects_capability_selection: bool = False
    affects_business_plan: bool = False
    authorizes_execution: bool = False
    launches_repair: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False

    unresolved_operation_count: int = Field(
        default=0,
        ge=0,
    )
    unresolved_operation_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_safety_boundary(
        self,
    ) -> "ObjectiveCandidateObservation":
        if not self.informational_only:
            raise ValueError(
                "Objective candidate observation must "
                "remain informational only"
            )

        if any(
            (
                self.affects_score,
                self.affects_ordering,
                self.affects_capability_selection,
                self.affects_business_plan,
                self.authorizes_execution,
                self.launches_repair,
                self.bypasses_approval,
                self.bypasses_verification,
            )
        ):
            raise ValueError(
                "Objective candidate observation cannot "
                "alter planning or execution"
            )

        if self.available and (
            self.state_kind
            == ObjectivePlanningStateKind.NO_CONTEXT
        ):
            raise ValueError(
                "Available objective observation cannot "
                "contain no_context state"
            )

        if not self.available and (
            self.state_kind
            != ObjectivePlanningStateKind.NO_CONTEXT
        ):
            raise ValueError(
                "Unavailable objective observation must "
                "contain no_context state"
            )

        if (
            self.objective_present
            != self.state.objective_present
        ):
            raise ValueError(
                "Objective presence must match the "
                "normalized planning state"
            )

        if (
            self.unresolved_operation_count
            != self.state.unresolved_operation_count
        ):
            raise ValueError(
                "Unresolved operation count must match "
                "the normalized planning state"
            )

        if (
            self.unresolved_operation_refs
            != self.state.unresolved_operation_refs
        ):
            raise ValueError(
                "Unresolved operation refs must match "
                "the normalized planning state"
            )

        return self


class ObjectiveCandidateObserver:
    """
    Attach normalized durable-objective facts to valid candidates.

    Every candidate and nested BusinessPlan is deep-copied.
    Existing metrics are retained. No candidate decision field changes.
    """

    observation_key = (
        OBJECTIVE_STATE_OBSERVATION_KEY
    )

    def observe(
        self,
        *,
        candidates: list[PlanCandidate],
        context: PlanningContext | None,
    ) -> list[PlanCandidate]:
        observation = self._observation(
            context=context
        )

        observed: list[PlanCandidate] = []

        for candidate in candidates:
            copied = candidate.model_copy(
                deep=True
            )

            metrics = deepcopy(copied.metrics)

            metrics[self.observation_key] = (
                observation.model_dump(
                    mode="json"
                )
            )

            copied.metrics = metrics
            observed.append(copied)

        return observed

    def _observation(
        self,
        *,
        context: PlanningContext | None,
    ) -> ObjectiveCandidateObservation:
        objective_context = (
            context.objective_context
            if context is not None
            else None
        )

        state = (
            ObjectivePlanningStateReasoner()
            .reason(objective_context)
        )

        available = objective_context is not None

        return ObjectiveCandidateObservation(
            available=available,
            objective_present=(
                state.objective_present
            ),
            state_kind=state.kind,
            state=state,
            unresolved_operation_count=(
                state.unresolved_operation_count
            ),
            unresolved_operation_refs=(
                state.unresolved_operation_refs
            ),
        )


__all__ = [
    "OBJECTIVE_STATE_OBSERVATION_KEY",
    "ObjectiveCandidateObservation",
    "ObjectiveCandidateObserver",
]
