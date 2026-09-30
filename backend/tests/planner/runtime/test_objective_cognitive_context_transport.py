from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContext,
    ObjectiveCognitiveIdentity,
    ObjectiveCognitiveProvenance,
    ObjectiveRepairCognitiveFact,
    ObjectiveResolutionCognitiveFact,
)
from app.tcos.planner.memory import PlanningMemory
from app.tcos.planner.runtime import PlannerRuntime
from app.tcos.planner.runtime.intent import (
    detect_intent,
)
from app.tcos.planner.runtime.objective_candidate_observation import (
    OBJECTIVE_STATE_OBSERVATION_KEY,
)
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)
from app.tcos.planner.runtime.planning_inputs import (
    build_default_planning_context,
)


GOAL = (
    "Summarize https://example.com"
)

NOW = datetime(
    2026,
    8,
    3,
    12,
    0,
    tzinfo=timezone.utc,
)


def _objective_context() -> ObjectiveCognitiveContext:
    resolution_record_id = uuid4()
    repair_execution_id = uuid4()

    return ObjectiveCognitiveContext(
        present=True,
        identity=ObjectiveCognitiveIdentity(
            namespace="customer_service.support",
            objective_ref="review-plan-1001",
            objective_type="multi_operation",
            objective_version=3,
        ),
        resolution=ObjectiveResolutionCognitiveFact(
            resolution_record_id=(
                resolution_record_id
            ),
            source_event_id=uuid4(),
            tenant_id="tenant-1",
            workflow_run_id="workflow-run-original",
            status="failed",
            reason_code=(
                "one_or_more_operations_failed"
            ),
            summary=(
                "The required refund operation failed."
            ),
            confidence=0.95,
            is_terminal=False,
            source_outcome_ref="support-outcome-1",
            outcome_version=1,
            source_evaluation_ref=(
                "support-evaluation-1"
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
            created_at=NOW,
        ),
        latest_repair=ObjectiveRepairCognitiveFact(
            repair_execution_id=(
                repair_execution_id
            ),
            resolution_record_id=(
                resolution_record_id
            ),
            source_event_id=uuid4(),
            status="rejected",
            attempt_number=1,
            repair_request_ref=(
                "objective-repair:resolution:v1"
            ),
            repair_request_version=1,
            planner_ref=(
                "customer_support_objective_repair"
            ),
            planner_policy_version=1,
            disposition="replan_remaining",
            reason_code=(
                "support_repair_requires_replanning"
            ),
            summary=(
                "The repair was rejected at approval."
            ),
            confidence=0.94,
            automatic_execution_allowed=False,
            human_approval_required=True,
            workflow_job_id=uuid4(),
            workflow_run_id="workflow-run-repair",
            runtime_status="ok",
            repair_result_status="rejected",
            created_at=NOW,
            completed_at=NOW,
        ),
        provenance=ObjectiveCognitiveProvenance(
            resolution_record_id=(
                resolution_record_id
            ),
            repair_execution_id=(
                repair_execution_id
            ),
        ),
    )


def _without_objective_transport(
    value: dict,
) -> dict:
    copied = deepcopy(value)
    copied.pop("objective_context", None)
    return copied


def test_planning_context_accepts_typed_objective_context():
    objective_context = _objective_context()

    context = PlanningContext(
        user_message=GOAL,
        objective_context=objective_context,
    )

    assert context.objective_context == (
        objective_context
    )
    assert (
        context.objective_context
        .resolution
        .status
        == "failed"
    )
    assert (
        context.objective_context
        .latest_repair
        .status
        == "rejected"
    )


def test_default_builder_transports_objective_context():
    objective_context = _objective_context()

    context = build_default_planning_context(
        user_message=GOAL,
        objective_context=objective_context,
    )

    assert context.objective_context == (
        objective_context
    )
    assert context.user_message == GOAL


def test_default_builder_remains_backward_compatible():
    context = build_default_planning_context(
        user_message=GOAL
    )

    assert context.objective_context is None
    assert context.user_message == GOAL


def test_planner_session_serializes_objective_context():
    objective_context = _objective_context()

    context = PlanningContext(
        user_message=GOAL,
        objective_context=objective_context,
    )

    session = PlannerRuntime().plan_goal(
        goal=GOAL,
        user_id=str(uuid4()),
        tenant_id="tenant-1",
        planning_context=context,
    )

    serialized = session.context[
        "objective_context"
    ]

    assert serialized["present"] is True
    assert serialized["identity"][
        "namespace"
    ] == "customer_service.support"
    assert serialized["resolution"][
        "status"
    ] == "failed"
    assert serialized["latest_repair"][
        "status"
    ] == "rejected"
    assert serialized["safety"][
        "affects_ranking"
    ] is False
    assert serialized["safety"][
        "authorizes_execution"
    ] is False


def test_planner_does_not_mutate_supplied_context():
    objective_context = _objective_context()

    context = PlanningContext(
        user_message=GOAL,
        objective_context=objective_context,
    )
    before = context.model_dump(
        mode="python"
    )

    PlannerRuntime().plan_goal(
        goal=GOAL,
        planning_context=context,
    )

    assert context.model_dump(
        mode="python"
    ) == before


def test_objective_transport_does_not_change_plan_decisions():
    baseline = PlannerRuntime().plan_goal(
        goal=GOAL,
    )

    observed = PlannerRuntime().plan_goal(
        goal=GOAL,
        planning_context=PlanningContext(
            user_message=GOAL,
            objective_context=(
                _objective_context()
            ),
        ),
    )

    baseline_candidate = deepcopy(
        baseline.selected_candidate
    )
    observed_candidate = deepcopy(
        observed.selected_candidate
    )

    baseline_observation = (
        baseline_candidate["metrics"].pop(
            OBJECTIVE_STATE_OBSERVATION_KEY
        )
    )
    observed_observation = (
        observed_candidate["metrics"].pop(
            OBJECTIVE_STATE_OBSERVATION_KEY
        )
    )

    assert baseline_candidate == (
        observed_candidate
    )

    assert baseline_observation[
        "available"
    ] is False
    assert baseline_observation[
        "state_kind"
    ] == "no_context"

    assert observed_observation[
        "available"
    ] is True
    assert observed_observation[
        "objective_present"
    ] is True
    assert observed_observation[
        "state_kind"
    ] in {
        "unresolved",
        "repair_active",
        "repair_terminal",
        "resolved",
        "absent",
    }

    for observation in (
        baseline_observation,
        observed_observation,
    ):
        assert (
            observation["informational_only"]
            is True
        )
        assert (
            observation["affects_score"]
            is False
        )
        assert (
            observation["affects_ordering"]
            is False
        )
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
        assert (
            observation["launches_repair"]
            is False
        )
        assert (
            observation[
                "bypasses_approval"
            ]
            is False
        )
        assert (
            observation[
                "bypasses_verification"
            ]
            is False
        )
    assert baseline.business_plan == (
        observed.business_plan
    )
    assert baseline.compilation == (
        observed.compilation
    )
    assert baseline.verification_result == (
        observed.verification_result
    )
    assert baseline.repair_result == (
        observed.repair_result
    )


def test_objective_transport_does_not_change_metrics():
    baseline = PlannerRuntime().plan_goal(
        goal=GOAL,
    )

    observed = PlannerRuntime().plan_goal(
        goal=GOAL,
        planning_context=PlanningContext(
            user_message=GOAL,
            objective_context=(
                _objective_context()
            ),
        ),
    )

    assert baseline.metrics == observed.metrics


def test_objective_transport_does_not_change_event_sequence():
    baseline = PlannerRuntime().plan_goal(
        goal=GOAL,
    )

    observed = PlannerRuntime().plan_goal(
        goal=GOAL,
        planning_context=PlanningContext(
            user_message=GOAL,
            objective_context=(
                _objective_context()
            ),
        ),
    )

    assert [
        event.type
        for event in baseline.events
    ] == [
        event.type
        for event in observed.events
    ]


def test_objective_transport_does_not_change_memory_retrieval():
    intent = detect_intent(text=GOAL)
    memory = PlanningMemory()

    baseline = memory.retrieve(
        intent=intent,
        context=PlanningContext(
            user_message=GOAL,
        ),
    )

    observed = memory.retrieve(
        intent=intent,
        context=PlanningContext(
            user_message=GOAL,
            objective_context=(
                _objective_context()
            ),
        ),
    )

    assert baseline == observed


def test_only_session_context_differs_by_objective_transport():
    baseline = PlannerRuntime().plan_goal(
        goal=GOAL,
    )

    observed = PlannerRuntime().plan_goal(
        goal=GOAL,
        planning_context=PlanningContext(
            user_message=GOAL,
            objective_context=(
                _objective_context()
            ),
        ),
    )

    baseline_context = (
        _without_objective_transport(
            baseline.context
        )
    )
    observed_context = (
        _without_objective_transport(
            observed.context
        )
    )

    assert baseline_context == observed_context
    assert baseline.context[
        "objective_context"
    ] is None
    assert observed.context[
        "objective_context"
    ] is not None
