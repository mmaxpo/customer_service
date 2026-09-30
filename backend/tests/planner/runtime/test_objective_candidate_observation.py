from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContext,
    ObjectiveCognitiveIdentity,
    ObjectiveCognitiveProvenance,
    ObjectiveResolutionCognitiveFact,
)
from app.tcos.planner.memory import PlanningMemory
from app.tcos.planner.runtime.advisory_observation import (
    ADVISORY_OBSERVATION_KEY,
)
from app.tcos.planner.runtime.intent import (
    detect_intent,
)
from app.tcos.planner.runtime.objective_candidate_observation import (
    OBJECTIVE_STATE_OBSERVATION_KEY,
    ObjectiveCandidateObservation,
    ObjectiveCandidateObserver,
)
from app.tcos.planner.runtime.objective_state_reasoner import (
    ObjectivePlanningStateKind,
    ObjectivePlanningStateReasoner,
)
from app.tcos.planner.runtime.plan_candidate import (
    PlanCandidate,
)
from app.tcos.planner.runtime.plan_evaluator import (
    PlanEvaluator,
)
from app.tcos.planner.runtime.plan_generator import (
    PlanGenerator,
)
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)


GOAL = "Summarize https://example.com"


def _objective_context():
    resolution_id = uuid4()

    return ObjectiveCognitiveContext(
        present=True,
        identity=ObjectiveCognitiveIdentity(
            namespace="customer_service.support",
            objective_ref="review-plan-1",
            objective_type="multi_operation",
            objective_version=1,
        ),
        resolution=(
            ObjectiveResolutionCognitiveFact(
                resolution_record_id=(
                    resolution_id
                ),
                source_event_id=uuid4(),
                tenant_id="tenant-1",
                workflow_run_id="run-1",
                status="failed",
                reason_code="operation_failed",
                summary="Refund operation failed.",
                confidence=0.95,
                is_terminal=False,
                source_outcome_ref="outcome-1",
                outcome_version=1,
                source_evaluation_ref=(
                    "evaluation-1"
                ),
                evaluation_version=1,
                projection_version=1,
                operation_count=1,
                achieved_operation_count=0,
                unresolved_operation_count=1,
                failed_operation_count=1,
                pending_operation_count=0,
                unknown_operation_count=0,
                not_executed_operation_count=0,
                unresolved_operation_refs=(
                    "support-operation:refund",
                ),
                failed_operation_refs=(
                    "support-operation:refund",
                ),
                created_at=datetime(
                    2026,
                    8,
                    3,
                    12,
                    0,
                    tzinfo=timezone.utc,
                ),
            )
        ),
        provenance=ObjectiveCognitiveProvenance(
            resolution_record_id=resolution_id,
        ),
    )


def _contexts():
    return (
        PlanningContext(
            user_message=GOAL,
        ),
        PlanningContext(
            user_message=GOAL,
            objective_context=(
                _objective_context()
            ),
        ),
    )


def _without_objective_observation(
    metrics: dict,
) -> dict:
    copied = deepcopy(metrics)

    copied.pop(
        OBJECTIVE_STATE_OBSERVATION_KEY,
        None,
    )

    return copied


def test_generator_records_no_context_observation():
    candidate = PlanGenerator().generate(
        intent=detect_intent(text=GOAL),
        context=PlanningContext(
            user_message=GOAL
        ),
    )[0]

    observation = candidate.metrics[
        OBJECTIVE_STATE_OBSERVATION_KEY
    ]

    assert observation["available"] is False
    assert observation["objective_present"] is False
    assert observation["state_kind"] == "no_context"
    assert observation["informational_only"] is True
    assert observation["affects_score"] is False
    assert observation["affects_ordering"] is False
    assert (
        observation[
            "affects_capability_selection"
        ]
        is False
    )
    assert (
        observation[
            "affects_business_plan"
        ]
        is False
    )
    assert (
        observation[
            "authorizes_execution"
        ]
        is False
    )
    assert observation["launches_repair"] is False


def test_generator_observes_unresolved_objective():
    _, objective_context = _contexts()

    candidate = PlanGenerator().generate(
        intent=detect_intent(text=GOAL),
        context=objective_context,
    )[0]

    observation = candidate.metrics[
        OBJECTIVE_STATE_OBSERVATION_KEY
    ]

    assert observation["available"] is True
    assert observation["objective_present"] is True
    assert observation["state_kind"] == "unresolved"
    assert (
        observation[
            "unresolved_operation_count"
        ]
        == 1
    )
    assert observation[
        "unresolved_operation_refs"
    ] == [
        "support-operation:refund"
    ]
    assert observation["state"]["kind"] == (
        "unresolved"
    )


def test_objective_observation_does_not_change_candidate():
    base, objective = _contexts()
    intent = detect_intent(text=GOAL)

    baseline = PlanGenerator().generate(
        intent=intent,
        context=base,
    )
    observed = PlanGenerator().generate(
        intent=intent,
        context=objective,
    )

    assert len(baseline) == len(observed)

    for plain, with_objective in zip(
        baseline,
        observed,
        strict=True,
    ):
        assert plain.id == with_objective.id
        assert plain.source == with_objective.source
        assert plain.score == with_objective.score
        assert (
            plain.explanation
            == with_objective.explanation
        )
        assert (
            plain.business_plan
            == with_objective.business_plan
        )

        plain_metrics = (
            _without_objective_observation(
                plain.metrics
            )
        )
        observed_metrics = (
            _without_objective_observation(
                with_objective.metrics
            )
        )

        assert plain_metrics == observed_metrics


def test_evaluator_scores_and_ordering_are_identical():
    base, objective = _contexts()
    intent = detect_intent(text=GOAL)

    baseline = PlanEvaluator().evaluate(
        PlanGenerator().generate(
            intent=intent,
            context=base,
        )
    )

    observed = PlanEvaluator().evaluate(
        PlanGenerator().generate(
            intent=intent,
            context=objective,
        )
    )

    assert [
        item.score
        for item in baseline
    ] == [
        item.score
        for item in observed
    ]

    assert [
        item.id
        for item in sorted(
            baseline,
            key=lambda item: item.score,
            reverse=True,
        )
    ] == [
        item.id
        for item in sorted(
            observed,
            key=lambda item: item.score,
            reverse=True,
        )
    ]


def test_existing_advisory_observation_is_preserved():
    _, objective = _contexts()

    candidate = PlanGenerator().generate(
        intent=detect_intent(text=GOAL),
        context=objective,
    )[0]

    assert (
        OBJECTIVE_STATE_OBSERVATION_KEY
        in candidate.metrics
    )
    assert (
        ADVISORY_OBSERVATION_KEY
        in candidate.metrics
    )


def test_observer_does_not_mutate_candidate():
    base, objective = _contexts()

    original = PlanGenerator().generate(
        intent=detect_intent(text=GOAL),
        context=base,
    )[0]

    before = original.model_dump(
        mode="python"
    )

    result = (
        ObjectiveCandidateObserver()
        .observe(
            candidates=[original],
            context=objective,
        )
    )

    assert original.model_dump(
        mode="python"
    ) == before

    assert result[0] is not original
    assert (
        result[0].business_plan
        is not original.business_plan
    )


def test_memory_candidate_is_copied_before_observation():
    memory = PlanningMemory()
    memory.clear()

    base, objective = _contexts()
    intent = detect_intent(text=GOAL)

    seed = PlanGenerator().generate(
        intent=intent,
        context=base,
    )[0]

    stored = memory.record_success(
        intent_name=intent.name,
        candidate=PlanCandidate(
            id="memory_objective_candidate",
            source="template",
            business_plan=(
                seed.business_plan
                .model_copy(deep=True)
            ),
            metrics={
                "historical_bonus": 0.25,
            },
        ),
    )

    stored_before = stored.model_dump(
        mode="python"
    )

    generated = PlanGenerator().generate(
        intent=intent,
        context=objective,
    )

    memory_candidate = next(
        item
        for item in generated
        if item.id
        == "memory_objective_candidate"
    )

    assert (
        memory_candidate.metrics[
            "historical_bonus"
        ]
        == 0.25
    )

    assert (
        memory_candidate.metrics[
            OBJECTIVE_STATE_OBSERVATION_KEY
        ]["available"]
        is True
    )

    retrieved_after = (
        memory.retrieve(
            intent=intent,
            context=base,
        )[0]
        .candidate
    )

    assert retrieved_after.model_dump(
        mode="python"
    ) == stored_before["candidate"]

    memory.clear()


def test_observation_contract_rejects_influence():
    state = (
        ObjectivePlanningStateReasoner()
        .reason(None)
    )

    with pytest.raises(ValidationError):
        ObjectiveCandidateObservation(
            available=False,
            objective_present=False,
            state_kind=(
                ObjectivePlanningStateKind
                .NO_CONTEXT
            ),
            state=state,
            affects_score=True,
        )


def test_observation_contract_is_immutable():
    state = (
        ObjectivePlanningStateReasoner()
        .reason(None)
    )

    observation = (
        ObjectiveCandidateObservation(
            available=False,
            objective_present=False,
            state_kind=(
                ObjectivePlanningStateKind
                .NO_CONTEXT
            ),
            state=state,
        )
    )

    with pytest.raises(ValidationError):
        observation.available = True
