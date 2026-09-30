from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContext,
    ObjectiveCognitiveIdentity,
    ObjectiveCognitiveProvenance,
    ObjectiveCognitiveReference,
)
from app.tcos.cognitive import (
    OBJECTIVE_LIFECYCLE_TELEMETRY_EVENT,
    OBJECTIVE_LIFECYCLE_TELEMETRY_METRIC_KEY,
    CognitiveRuntime,
    ObjectiveLifecycleSessionTelemetry,
    ObjectiveLifecycleTelemetryProjector,
    ObjectiveRepairDelegationKind,
    ObjectiveRepairDelegationReasoner,
)
from app.tcos.planner.runtime.objective_candidate_observation import (
    OBJECTIVE_STATE_OBSERVATION_KEY,
    ObjectiveCandidateObservation,
)
from app.tcos.planner.runtime.objective_state_reasoner import (
    ObjectivePlanningStateReasoner,
)


def _absent_context() -> ObjectiveCognitiveContext:
    return ObjectiveCognitiveContext(
        present=False,
        identity=ObjectiveCognitiveIdentity(
            namespace="customer_service.support",
            objective_ref="review-plan-1",
            objective_type="multi_operation",
            objective_version=1,
        ),
        provenance=ObjectiveCognitiveProvenance(),
    )


def _planner_session(context):
    state = ObjectivePlanningStateReasoner().reason(context)

    observation = ObjectiveCandidateObservation(
        available=True,
        objective_present=state.objective_present,
        state_kind=state.kind,
        state=state,
        unresolved_operation_count=(state.unresolved_operation_count),
        unresolved_operation_refs=(state.unresolved_operation_refs),
    )

    return {
        "selected_candidate": {
            "id": "candidate-1",
            "metrics": {
                OBJECTIVE_STATE_OBSERVATION_KEY: (observation.model_dump(mode="json"))
            },
        }
    }


def test_projector_joins_objective_and_candidate_state():
    context = _absent_context()
    decision = ObjectiveRepairDelegationReasoner().reason(context)

    telemetry = ObjectiveLifecycleTelemetryProjector().project(
        objective_context=context,
        planner_session=_planner_session(context),
        delegation=decision,
    )

    assert telemetry.context_available is True
    assert telemetry.objective_present is False
    assert telemetry.resolution_available is False
    assert telemetry.repair_available is False
    assert telemetry.state_kind == "absent"

    assert telemetry.selected_candidate_observed is True

    assert telemetry.delegation_kind == (ObjectiveRepairDelegationKind.NO_DELEGATION)
    assert telemetry.repair_planning_requested is False

    assert telemetry.informational_only is True
    assert telemetry.affects_score is False
    assert telemetry.affects_ordering is False
    assert telemetry.persists_repair is False
    assert telemetry.launches_repair is False
    assert telemetry.authorizes_execution is False


def test_projector_does_not_mutate_planner_session():
    context = _absent_context()
    decision = ObjectiveRepairDelegationReasoner().reason(context)
    planner_session = _planner_session(context)

    before = {
        "selected_candidate": {
            "id": planner_session["selected_candidate"]["id"],
            "metrics": {
                OBJECTIVE_STATE_OBSERVATION_KEY: dict(
                    planner_session["selected_candidate"]["metrics"][
                        OBJECTIVE_STATE_OBSERVATION_KEY
                    ]
                )
            },
        }
    }

    ObjectiveLifecycleTelemetryProjector().project(
        objective_context=context,
        planner_session=planner_session,
        delegation=decision,
    )

    assert planner_session == before


def test_missing_selected_candidate_is_observed_safely():
    context = _absent_context()
    decision = ObjectiveRepairDelegationReasoner().reason(context)

    telemetry = ObjectiveLifecycleTelemetryProjector().project(
        objective_context=context,
        planner_session={"selected_candidate": None},
        delegation=decision,
    )

    assert telemetry.selected_candidate_observed is False
    assert telemetry.state_kind == "absent"


def test_behavioral_telemetry_flags_are_rejected():
    with pytest.raises(
        ValidationError,
        match="cannot alter",
    ):
        ObjectiveLifecycleSessionTelemetry(affects_score=True)


def test_planning_request_requires_attempt_number():
    with pytest.raises(
        ValidationError,
        match="requires an attempt",
    ):
        ObjectiveLifecycleSessionTelemetry(
            context_available=True,
            state_kind="unresolved",
            delegation_kind=(ObjectiveRepairDelegationKind.REPAIR_PLANNING_REQUESTED),
            repair_planning_requested=True,
        )


@pytest.mark.asyncio
async def test_runtime_projects_lifecycle_for_reference(
    monkeypatch,
):
    from app.runtime.objectives.cognition import (
        ObjectiveCognitiveContextLoader,
    )

    context = _absent_context()

    load = AsyncMock(return_value=context)

    monkeypatch.setattr(
        ObjectiveCognitiveContextLoader,
        "load_for_objective",
        load,
    )

    session = await CognitiveRuntime().execute_goal_runtime(
        goal="Reply to customer",
        ctx=SimpleNamespace(
            db=object(),
            user_id=uuid4(),
            tenant_id="tenant-1",
        ),
        objective=ObjectiveCognitiveReference(
            namespace="customer_service.support",
            objective_ref="review-plan-1",
        ),
    )

    lifecycle = session.metrics[OBJECTIVE_LIFECYCLE_TELEMETRY_METRIC_KEY]

    assert lifecycle["context_available"] is True
    assert lifecycle["objective_present"] is False
    assert lifecycle["state_kind"] == "absent"
    assert lifecycle["repair_planning_requested"] is False

    events = [
        event
        for event in session.events
        if event.type == OBJECTIVE_LIFECYCLE_TELEMETRY_EVENT
    ]

    assert len(events) == 1
    assert events[0].payload == lifecycle

    assert session.metrics["cognitive_event_count"] == len(session.events)


@pytest.mark.asyncio
async def test_runtime_without_reference_remains_free():
    session = await CognitiveRuntime().execute_goal_runtime(
        goal="Reply to customer",
        ctx=object(),
    )

    assert OBJECTIVE_LIFECYCLE_TELEMETRY_METRIC_KEY not in session.metrics

    assert all(
        event.type != OBJECTIVE_LIFECYCLE_TELEMETRY_EVENT for event in session.events
    )


def test_synchronous_runtime_remains_lifecycle_free():
    session = CognitiveRuntime().execute_goal(goal="Reply to customer")

    assert OBJECTIVE_LIFECYCLE_TELEMETRY_METRIC_KEY not in session.metrics

    assert all(
        event.type != OBJECTIVE_LIFECYCLE_TELEMETRY_EVENT for event in session.events
    )
