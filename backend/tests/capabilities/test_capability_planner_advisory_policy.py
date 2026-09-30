from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.runtime.capabilities.execution.learning import (
    CapabilityPlannerAdvisory,
    CapabilityPlannerAdvisoryKind,
    CapabilityPlannerAdvisoryProvenance,
    CapabilityPlannerAdvisoryScope,
)
from app.tcos.capabilities.planner_advisory_policy import (
    CapabilityPlannerAdvisoryPolicy,
    CapabilityPlannerContextItemKind,
)


NOW = datetime(
    2026,
    7,
    20,
    12,
    0,
    tzinfo=timezone.utc,
)


def _advisory(
    *,
    kind,
    statement,
    recommended_behavior,
    limitations=(),
    promotion_id=None,
):
    return CapabilityPlannerAdvisory(
        advisory_kind=kind,
        scope=CapabilityPlannerAdvisoryScope(
            tenant_id="tenant-a",
            capability_id=(
                "ecommerce.orders.get"
            ),
            provider_id="shopify",
            provider_ref=(
                "shopify.orders.get"
            ),
            action="read",
        ),
        statement=statement,
        recommended_behavior=(
            recommended_behavior
        ),
        limitations=limitations,
        provenance=(
            CapabilityPlannerAdvisoryProvenance(
                promotion_id=(
                    promotion_id or uuid4()
                ),
                promotion_event_version=1,
                candidate_id=uuid4(),
                candidate_version=1,
                evidence_fingerprint=(
                    "a" * 64
                ),
                promoted_at=NOW,
                created_by_user_id=uuid4(),
            )
        ),
    )


def test_policy_separates_guidance_warning_and_constraints():
    guidance = _advisory(
        kind=(
            CapabilityPlannerAdvisoryKind
            .GUIDANCE
        ),
        statement="Stable success pattern.",
        recommended_behavior=(
            "Consider collecting the order "
            "reference first."
        ),
        limitations=(
            "Exact provider scope only.",
        ),
    )
    warning = _advisory(
        kind=(
            CapabilityPlannerAdvisoryKind
            .WARNING
        ),
        statement=(
            "Repeated failure when order "
            "reference is absent."
        ),
        recommended_behavior=(
            "Do not treat this as authority."
        ),
        limitations=(
            "Human approval remains required.",
        ),
    )

    context = (
        CapabilityPlannerAdvisoryPolicy()
        .consume([warning, guidance])
    )

    assert len(context.considerations) == 1
    assert len(context.cautions) == 1
    assert len(context.constraints) == 2

    assert (
        context.considerations[0].kind
        == CapabilityPlannerContextItemKind
        .CONSIDERATION
    )
    assert (
        context.cautions[0].kind
        == CapabilityPlannerContextItemKind
        .CAUTION
    )
    assert all(
        item.kind
        == CapabilityPlannerContextItemKind
        .CONSTRAINT
        for item in context.constraints
    )

    assert context.advisory_count == 2
    assert (
        context.informational_only is True
    )
    assert context.affects_ranking is False
    assert (
        context.affects_compatibility
        is False
    )
    assert context.selects_provider is False
    assert (
        context.authorizes_execution
        is False
    )
    assert (
        context.bypasses_approval is False
    )
    assert (
        context.bypasses_verification
        is False
    )


def test_policy_is_deterministic():
    first_id = uuid4()
    second_id = uuid4()

    first = _advisory(
        kind=(
            CapabilityPlannerAdvisoryKind
            .GUIDANCE
        ),
        statement="First.",
        recommended_behavior="Consider first.",
        promotion_id=first_id,
    )
    second = _advisory(
        kind=(
            CapabilityPlannerAdvisoryKind
            .WARNING
        ),
        statement="Second.",
        recommended_behavior=(
            "Consider second."
        ),
        promotion_id=second_id,
    )

    policy = CapabilityPlannerAdvisoryPolicy()

    left = policy.consume([first, second])
    right = policy.consume([second, first])

    assert left == right


def test_policy_caps_each_section():
    advisories = [
        _advisory(
            kind=(
                CapabilityPlannerAdvisoryKind
                .GUIDANCE
            ),
            statement=f"Statement {index}",
            recommended_behavior=(
                f"Consideration {index}"
            ),
            limitations=(
                f"Constraint {index}",
            ),
        )
        for index in range(5)
    ]

    context = (
        CapabilityPlannerAdvisoryPolicy(
            maximum_items_per_section=2
        )
        .consume(advisories)
    )

    assert len(context.considerations) == 2
    assert len(context.constraints) == 2
    assert context.advisory_count == 5


def test_policy_rejects_invalid_limit():
    with pytest.raises(
        ValueError,
        match="between 1 and 100",
    ):
        CapabilityPlannerAdvisoryPolicy(
            maximum_items_per_section=0
        )
