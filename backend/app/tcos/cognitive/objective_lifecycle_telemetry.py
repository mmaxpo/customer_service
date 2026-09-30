from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator,
)

from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContext,
)
from app.tcos.cognitive.objective_repair_delegation import (
    ObjectiveRepairDelegationDecision,
    ObjectiveRepairDelegationKind,
)
from app.tcos.planner.runtime.objective_candidate_observation import (
    OBJECTIVE_STATE_OBSERVATION_KEY,
    ObjectiveCandidateObservation,
)
from app.tcos.planner.runtime.objective_state_reasoner import (
    ObjectivePlanningStateKind,
    ObjectivePlanningStateReasoner,
)


OBJECTIVE_LIFECYCLE_TELEMETRY_METRIC_KEY = "objective_lifecycle_telemetry"

OBJECTIVE_LIFECYCLE_TELEMETRY_EVENT = "ObjectiveLifecycleObserved"


class ObjectiveLifecycleSessionTelemetry(BaseModel):
    """
    Session-level observational projection of one durable objective.

    The projection joins the objective context, normalized planning
    state, selected-candidate observation, and repair-delegation
    decision. It cannot alter planning or execution behavior.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    schema_version: str = "objective_lifecycle_session_telemetry.v1"

    context_available: bool = False
    objective_present: bool = False
    resolution_available: bool = False
    repair_available: bool = False

    state_kind: ObjectivePlanningStateKind = ObjectivePlanningStateKind.NO_CONTEXT

    selected_candidate_observed: bool = False

    delegation_kind: ObjectiveRepairDelegationKind = (
        ObjectiveRepairDelegationKind.NO_DELEGATION
    )
    repair_planning_requested: bool = False
    requested_attempt_number: int | None = None

    resolution_record_id: UUID | None = None
    repair_execution_id: UUID | None = None

    informational_only: bool = True

    affects_score: bool = False
    affects_ordering: bool = False
    affects_capability_selection: bool = False
    affects_business_plan: bool = False

    persists_repair: bool = False
    publishes_platform_event: bool = False
    enqueues_job: bool = False
    launches_repair: bool = False
    authorizes_execution: bool = False

    bypasses_approval: bool = False
    bypasses_verification: bool = False

    @model_validator(mode="after")
    def validate_safety_boundary(
        self,
    ) -> "ObjectiveLifecycleSessionTelemetry":
        if not self.informational_only:
            raise ValueError(
                "Objective lifecycle telemetry must remain informational only"
            )

        if any(
            (
                self.affects_score,
                self.affects_ordering,
                self.affects_capability_selection,
                self.affects_business_plan,
                self.persists_repair,
                self.publishes_platform_event,
                self.enqueues_job,
                self.launches_repair,
                self.authorizes_execution,
                self.bypasses_approval,
                self.bypasses_verification,
            )
        ):
            raise ValueError(
                "Objective lifecycle telemetry cannot alter "
                "planning, persistence, or execution"
            )

        if not self.context_available and (
            self.state_kind != ObjectivePlanningStateKind.NO_CONTEXT
        ):
            raise ValueError(
                "Unavailable objective lifecycle context must use no_context state"
            )

        if self.repair_planning_requested and self.delegation_kind not in {
            (ObjectiveRepairDelegationKind.REPAIR_PLANNING_REQUESTED),
            (ObjectiveRepairDelegationKind.SUBSEQUENT_REPAIR_PLANNING_REQUESTED),
        }:
            raise ValueError(
                "Repair-planning request must use a planning delegation kind"
            )

        if (
            self.requested_attempt_number is not None
            and self.requested_attempt_number < 1
        ):
            raise ValueError("Requested repair attempt must be positive")

        if self.repair_planning_requested and self.requested_attempt_number is None:
            raise ValueError("Repair-planning request requires an attempt number")

        return self


class ObjectiveLifecycleTelemetryProjector:
    """
    Build one immutable cognitive-session lifecycle projection.

    The projector reads serialized selected-candidate metrics but
    never mutates the planner session, candidate, objective context,
    or repair-delegation decision.
    """

    def project(
        self,
        *,
        objective_context: (ObjectiveCognitiveContext | None),
        planner_session: dict[str, Any] | None,
        delegation: ObjectiveRepairDelegationDecision,
    ) -> ObjectiveLifecycleSessionTelemetry:
        state = ObjectivePlanningStateReasoner().reason(objective_context)

        observation = self._selected_observation(planner_session)

        if observation is not None:
            self._validate_observation(
                observation=observation,
                state_kind=state.kind,
                objective_present=state.objective_present,
            )

        resolution = (
            objective_context.resolution if objective_context is not None else None
        )
        repair = (
            objective_context.latest_repair if objective_context is not None else None
        )

        return ObjectiveLifecycleSessionTelemetry(
            context_available=(objective_context is not None),
            objective_present=state.objective_present,
            resolution_available=resolution is not None,
            repair_available=repair is not None,
            state_kind=state.kind,
            selected_candidate_observed=(observation is not None),
            delegation_kind=delegation.kind,
            repair_planning_requested=(delegation.requested),
            requested_attempt_number=(delegation.requested_attempt_number),
            resolution_record_id=(delegation.resolution_record_id),
            repair_execution_id=(delegation.repair_execution_id),
        )

    @staticmethod
    def _selected_observation(
        planner_session: dict[str, Any] | None,
    ) -> ObjectiveCandidateObservation | None:
        if not isinstance(planner_session, dict):
            return None

        candidate = planner_session.get("selected_candidate")

        if not isinstance(candidate, dict):
            return None

        metrics = candidate.get("metrics")

        if not isinstance(metrics, dict):
            return None

        raw = metrics.get(OBJECTIVE_STATE_OBSERVATION_KEY)

        if not isinstance(raw, dict):
            return None

        return ObjectiveCandidateObservation.model_validate(raw)

    @staticmethod
    def _validate_observation(
        *,
        observation: ObjectiveCandidateObservation,
        state_kind: ObjectivePlanningStateKind,
        objective_present: bool,
    ) -> None:
        if observation.state_kind != state_kind:
            raise ValueError(
                "Selected-candidate objective state does not "
                "match cognitive lifecycle state"
            )

        if observation.objective_present != objective_present:
            raise ValueError(
                "Selected-candidate objective presence does "
                "not match cognitive lifecycle state"
            )


__all__ = [
    "OBJECTIVE_LIFECYCLE_TELEMETRY_EVENT",
    "OBJECTIVE_LIFECYCLE_TELEMETRY_METRIC_KEY",
    "ObjectiveLifecycleSessionTelemetry",
    "ObjectiveLifecycleTelemetryProjector",
]
