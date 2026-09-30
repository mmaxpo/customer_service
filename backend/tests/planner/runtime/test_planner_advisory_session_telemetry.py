from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from app.tcos.capabilities.planner_advisory_renderer import (
    CapabilityPlannerRenderedContext,
)
from app.tcos.planner.runtime import (
    PlannerRuntime,
)
from app.tcos.planner.runtime.advisory_context_injection import (
    PlannerAdvisoryContextInjector,
)
from app.tcos.planner.runtime.advisory_telemetry import (
    PLANNER_ADVISORY_OBSERVED_EVENT,
)
from app.tcos.planner.runtime.planning_inputs import (
    build_default_planning_context,
)


GOAL = (
    "Summarize https://example.com"
)


def _injected_context():
    promotion_id = str(uuid4())

    rendered = CapabilityPlannerRenderedContext(
        present=True,
        text=(
            "Learned planner context\n"
            "This context is informational only."
        ),
        payload={
            "advisory_count": 1,
            "source_promotion_ids": [
                promotion_id
            ],
            "safety": {
                "informational_only": True,
                "affects_ranking": False,
            },
        },
    )

    base = build_default_planning_context(
        user_message=GOAL
    )

    result = (
        PlannerAdvisoryContextInjector()
        .inject(
            context=base,
            rendered_contexts=[rendered],
            enabled=True,
        )
    )

    return result.context, promotion_id


def _advisory_event(session):
    return next(
        event
        for event in session.events
        if event.type
        == PLANNER_ADVISORY_OBSERVED_EVENT
    )


def test_default_session_records_absent_advisory_telemetry():
    session = (
        PlannerRuntime()
        .plan_goal(
            goal=GOAL,
        )
    )

    assert (
        session.metrics[
            "advisory_context_available"
        ]
        is False
    )
    assert (
        session.metrics[
            "advisory_context_injected"
        ]
        is False
    )
    assert (
        session.metrics[
            "advisory_fragment_count"
        ]
        == 0
    )
    assert (
        session.metrics[
            "advisory_source_promotion_ids"
        ]
        == []
    )
    assert (
        session.metrics[
            "advisory_affects_score"
        ]
        is False
    )
    assert (
        session.metrics[
            "advisory_authorizes_execution"
        ]
        is False
    )

    event = _advisory_event(session)

    assert event.payload["available"] is False
    assert event.payload["injected"] is False
    assert event.payload["fragment_count"] == 0


def test_injected_session_surfaces_advisory_telemetry():
    context, promotion_id = (
        _injected_context()
    )

    session = (
        PlannerRuntime()
        .plan_goal(
            goal=GOAL,
            planning_context=context,
        )
    )

    assert (
        session.metrics[
            "advisory_context_available"
        ]
        is True
    )
    assert (
        session.metrics[
            "advisory_context_injected"
        ]
        is True
    )
    assert (
        session.metrics[
            "advisory_fragment_count"
        ]
        == 1
    )
    assert (
        session.metrics[
            "advisory_source_promotion_ids"
        ]
        == [promotion_id]
    )

    event = _advisory_event(session)

    assert event.payload["available"] is True
    assert event.payload["injected"] is True
    assert event.payload["fragment_count"] == 1
    assert (
        event.payload[
            "source_promotion_ids"
        ]
        == [promotion_id]
    )
    assert (
        event.payload[
            "affects_capability_selection"
        ]
        is False
    )
    assert (
        event.payload[
            "authorizes_execution"
        ]
        is False
    )


def test_session_telemetry_does_not_change_selected_plan():
    baseline = (
        PlannerRuntime()
        .plan_goal(
            goal=GOAL,
        )
    )

    context, _ = _injected_context()

    observed = (
        PlannerRuntime()
        .plan_goal(
            goal=GOAL,
            planning_context=context,
        )
    )

    baseline_candidate = deepcopy(
        baseline.selected_candidate
    )
    observed_candidate = deepcopy(
        observed.selected_candidate
    )

    baseline_observation = (
        baseline_candidate["metrics"].pop(
            "learning_advisory_observation"
        )
    )
    observed_observation = (
        observed_candidate["metrics"].pop(
            "learning_advisory_observation"
        )
    )

    assert (
        baseline_candidate
        == observed_candidate
    )
    assert (
        baseline.business_plan
        == observed.business_plan
    )
    assert (
        baseline.compilation
        == observed.compilation
    )
    assert (
        baseline.verification_result
        == observed.verification_result
    )

    assert (
        baseline_observation["injected"]
        is False
    )
    assert (
        observed_observation["injected"]
        is True
    )


def test_runtime_copies_supplied_planning_context():
    context, _ = _injected_context()
    before = context.model_dump(
        mode="python"
    )

    session = (
        PlannerRuntime()
        .plan_goal(
            goal=GOAL,
            planning_context=context,
        )
    )

    assert (
        context.model_dump(mode="python")
        == before
    )
    assert session.context == (
        context.model_dump(mode="json")
    )
