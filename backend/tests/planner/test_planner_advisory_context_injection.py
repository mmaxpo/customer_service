from __future__ import annotations

from copy import deepcopy

from app.tcos.capabilities.planner_advisory_renderer import (
    CapabilityPlannerRenderedContext,
)
from app.tcos.planner.runtime.advisory_context_injection import (
    ADVISORY_PREFERENCE_KEY,
    PlannerAdvisoryContextInjector,
)
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)


def _rendered(
    *,
    text: str = "Learned planner context",
):
    return CapabilityPlannerRenderedContext(
        present=True,
        text=text,
        payload={
            "advisory_count": 1,
            "safety": {
                "informational_only": True,
                "affects_ranking": False,
            },
        },
    )


def test_disabled_injection_returns_unchanged_copy():
    original = PlanningContext(
        user_message="Check order #1234",
        channel="chat",
        customer_id="customer-1",
        conversation_id="conversation-1",
        enabled_capabilities=[
            "shopify.get_order",
        ],
        planner_preferences={
            "preferred_language": "en",
        },
        execution_constraints={
            "requires_approval": True,
        },
    )
    before = original.model_dump(
        mode="python"
    )

    result = (
        PlannerAdvisoryContextInjector()
        .inject(
            context=original,
            rendered_contexts=[
                _rendered()
            ],
            enabled=False,
        )
    )

    assert result.requested is False
    assert result.injected is False
    assert result.fragment_count == 0
    assert (
        result.context.model_dump(
            mode="python"
        )
        == before
    )
    assert (
        original.model_dump(mode="python")
        == before
    )
    assert (
        result.context is not original
    )


def test_enabled_injection_requires_present_context():
    original = PlanningContext(
        user_message="Check order #1234",
    )

    absent = CapabilityPlannerRenderedContext(
        present=False,
        text="",
    )

    result = (
        PlannerAdvisoryContextInjector()
        .inject(
            context=original,
            rendered_contexts=[absent],
            enabled=True,
        )
    )

    assert result.requested is True
    assert result.injected is False
    assert result.fragment_count == 0
    assert (
        ADVISORY_PREFERENCE_KEY
        not in result.context
        .planner_preferences
    )


def test_enabled_injection_uses_reserved_namespace():
    original = PlanningContext(
        user_message="Check order #1234",
        channel="chat",
        enabled_capabilities=[
            "shopify.get_order",
        ],
        planner_preferences={
            "preferred_language": "en",
        },
        execution_constraints={
            "requires_approval": True,
        },
    )
    original_dump = original.model_dump(
        mode="python"
    )

    rendered = _rendered(
        text=(
            "Learned planner context\n"
            "This context is informational only."
        )
    )

    result = (
        PlannerAdvisoryContextInjector()
        .inject(
            context=original,
            rendered_contexts=[rendered],
            enabled=True,
        )
    )

    assert result.requested is True
    assert result.injected is True
    assert result.fragment_count == 1

    namespace = (
        result.context
        .planner_preferences[
            ADVISORY_PREFERENCE_KEY
        ]
    )

    assert namespace["enabled"] is True
    assert (
        namespace["informational_only"]
        is True
    )
    assert (
        namespace["affects_ranking"]
        is False
    )
    assert (
        namespace[
            "affects_capability_selection"
        ]
        is False
    )
    assert (
        namespace["authorizes_execution"]
        is False
    )
    assert len(namespace["fragments"]) == 1
    assert (
        namespace["fragments"][0]["text"]
        == rendered.text
    )
    assert (
        namespace["fragments"][0][
            "payload"
        ]
        == rendered.payload
    )

    assert (
        result.context.user_message
        == original.user_message
    )
    assert (
        result.context.channel
        == original.channel
    )
    assert (
        result.context.enabled_capabilities
        == original.enabled_capabilities
    )
    assert (
        result.context.execution_constraints
        == original.execution_constraints
    )
    assert (
        result.context.planner_preferences[
            "preferred_language"
        ]
        == "en"
    )

    assert (
        original.model_dump(mode="python")
        == original_dump
    )


def test_injection_is_deterministic_and_copies_payloads():
    original = PlanningContext(
        user_message="Summarize this URL",
    )
    rendered = _rendered()

    first = (
        PlannerAdvisoryContextInjector()
        .inject(
            context=original,
            rendered_contexts=[rendered],
            enabled=True,
        )
    )
    second = (
        PlannerAdvisoryContextInjector()
        .inject(
            context=original,
            rendered_contexts=[rendered],
            enabled=True,
        )
    )

    assert first == second

    stored_payload = (
        first.context
        .planner_preferences[
            ADVISORY_PREFERENCE_KEY
        ]["fragments"][0]["payload"]
    )

    before = deepcopy(stored_payload)
    rendered.payload["changed"] = True

    assert stored_payload == before
