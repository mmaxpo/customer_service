from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from app.tcos.capabilities.planner_advisory_renderer import (
    CapabilityPlannerRenderedContext,
)
from app.tcos.planner.memory import (
    PlanningMemory,
)
from app.tcos.planner.runtime.advisory_context_injection import (
    PlannerAdvisoryContextInjector,
)
from app.tcos.planner.runtime.advisory_observation import (
    ADVISORY_OBSERVATION_KEY,
    PlannerAdvisoryObserver,
)
from app.tcos.planner.runtime.intent import (
    detect_intent,
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
from app.tcos.planner.runtime.planning_inputs import (
    build_default_planning_context,
)


def _rendered():
    promotion_id = str(uuid4())

    return CapabilityPlannerRenderedContext(
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


def _contexts():
    base = build_default_planning_context(
        user_message=(
            "Summarize https://example.com"
        )
    )

    injected = (
        PlannerAdvisoryContextInjector()
        .inject(
            context=base,
            rendered_contexts=[
                _rendered()
            ],
            enabled=True,
        )
        .context
    )

    return base, injected


def test_observer_records_absence_without_influence():
    base, _ = _contexts()

    candidates = PlanGenerator().generate(
        intent=detect_intent(
            text=base.user_message
        ),
        context=base,
    )

    observation = candidates[0].metrics[
        ADVISORY_OBSERVATION_KEY
    ]

    assert observation["available"] is False
    assert observation["injected"] is False
    assert observation["fragment_count"] == 0
    assert observation["affects_score"] is False
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


def test_generator_observes_injection_without_changing_plan():
    base, injected = _contexts()
    intent = detect_intent(
        text=base.user_message
    )

    baseline = PlanGenerator().generate(
        intent=intent,
        context=base,
    )
    observed = PlanGenerator().generate(
        intent=intent,
        context=injected,
    )

    assert len(baseline) == len(observed)

    for plain, with_advisory in zip(
        baseline,
        observed,
        strict=True,
    ):
        assert plain.id == with_advisory.id
        assert plain.source == with_advisory.source
        assert plain.score == with_advisory.score
        assert (
            plain.explanation
            == with_advisory.explanation
        )
        assert (
            plain.business_plan
            == with_advisory.business_plan
        )

        plain_metrics = deepcopy(
            plain.metrics
        )
        observed_metrics = deepcopy(
            with_advisory.metrics
        )

        plain_observation = plain_metrics.pop(
            ADVISORY_OBSERVATION_KEY
        )
        advisory_observation = (
            observed_metrics.pop(
                ADVISORY_OBSERVATION_KEY
            )
        )

        assert plain_metrics == observed_metrics
        assert (
            plain_observation["available"]
            is False
        )
        assert (
            advisory_observation["available"]
            is True
        )
        assert (
            advisory_observation["injected"]
            is True
        )
        assert (
            advisory_observation[
                "fragment_count"
            ]
            == 1
        )
        assert len(
            advisory_observation[
                "source_promotion_ids"
            ]
        ) == 1


def test_evaluator_scores_are_identical():
    base, injected = _contexts()
    intent = detect_intent(
        text=base.user_message
    )

    baseline = PlanEvaluator().evaluate(
        PlanGenerator().generate(
            intent=intent,
            context=base,
        )
    )
    observed = PlanEvaluator().evaluate(
        PlanGenerator().generate(
            intent=intent,
            context=injected,
        )
    )

    assert [
        candidate.score
        for candidate in baseline
    ] == [
        candidate.score
        for candidate in observed
    ]

    assert [
        candidate.id
        for candidate in sorted(
            baseline,
            key=lambda item: item.score,
            reverse=True,
        )
    ] == [
        candidate.id
        for candidate in sorted(
            observed,
            key=lambda item: item.score,
            reverse=True,
        )
    ]


def test_observer_does_not_mutate_candidates():
    base, injected = _contexts()

    original = PlanGenerator().generate(
        intent=detect_intent(
            text=base.user_message
        ),
        context=base,
    )[0]

    before = original.model_dump(
        mode="python"
    )

    result = PlannerAdvisoryObserver().observe(
        candidates=[original],
        context=injected,
    )

    assert (
        original.model_dump(mode="python")
        == before
    )
    assert result[0] is not original
    assert (
        result[0].business_plan
        is not original.business_plan
    )


def test_memory_candidate_is_copied_before_observation():
    memory = PlanningMemory()
    memory.clear()

    base, injected = _contexts()
    intent = detect_intent(
        text=base.user_message
    )

    seed = PlanGenerator().generate(
        intent=intent,
        context=base,
    )[0]

    stored = memory.record_success(
        intent_name=intent.name,
        candidate=PlanCandidate(
            id="memory_candidate",
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
        context=injected,
    )

    memory_candidate = next(
        candidate
        for candidate in generated
        if candidate.id
        == "memory_candidate"
    )

    assert (
        memory_candidate.metrics[
            "historical_bonus"
        ]
        == 0.25
    )
    assert (
        memory_candidate.metrics[
            ADVISORY_OBSERVATION_KEY
        ]["injected"]
        is True
    )

    retrieved_after = (
        memory.retrieve(
            intent=intent,
            context=base,
        )[0]
        .candidate
    )

    assert (
        retrieved_after.model_dump(
            mode="python"
        )
        == stored_before["candidate"]
    )

    memory.clear()
