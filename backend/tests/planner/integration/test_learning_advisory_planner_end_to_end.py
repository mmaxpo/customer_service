from __future__ import annotations

from copy import deepcopy
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.capabilities.execution.learning import (
    CapabilityLearningAdvisoryStatus,
    CapabilityLearningInsightCandidateFactory,
    CapabilityLearningInsightCandidateRepository,
    CapabilityLearningInsightPromotionRepository,
    CapabilityLearningInterpretation,
    CapabilityLearningPromotionFactory,
    CapabilityLearningQualityLevel,
    CapabilityLearningStabilityLevel,
    CapabilityLearningSummary,
    CapabilityLearningTrendDirection,
    CapabilityLearningTrendReport,
    CapabilityPlannerAdvisoryService,
)
from app.tcos.capabilities.planner_advisory_policy import (
    CapabilityPlannerAdvisoryPolicy,
)
from app.tcos.capabilities.planner_advisory_renderer import (
    CapabilityPlannerAdvisoryRenderer,
)
from app.tcos.planner.runtime.advisory_telemetry import (
    PLANNER_ADVISORY_OBSERVED_EVENT,
    PlannerAdvisorySessionTelemetry,
)
from app.tcos.planner.runtime import (
    PlannerRuntime,
)
from app.tcos.planner.runtime.advisory_context_injection import (
    PlannerAdvisoryContextInjector,
)
from app.tcos.planner.runtime.advisory_observation import (
    ADVISORY_OBSERVATION_KEY,
)
from app.tcos.planner.runtime.planning_inputs import (
    build_default_planning_context,
)


NOW = datetime(
    2026,
    7,
    20,
    12,
    0,
    tzinfo=timezone.utc,
)

GOAL = (
    "Summarize https://example.com"
)

CAPABILITY_ID = "ecommerce.orders.get"
PROVIDER_ID = "shopify"
PROVIDER_REF = "shopify.orders.get"
TENANT_ID = "tenant-learning-planner-e2e"
ACTION = "read"


def _summary(
    *,
    recent: bool,
) -> CapabilityLearningSummary:
    start = (
        NOW - timedelta(days=7)
        if recent
        else NOW - timedelta(days=14)
    )
    end = (
        NOW
        if recent
        else NOW - timedelta(days=7)
    )

    return CapabilityLearningSummary(
        capability_id=CAPABILITY_ID,
        provider_id=PROVIDER_ID,
        provider_ref=PROVIDER_REF,
        tenant_id=TENANT_ID,
        action=ACTION,
        window_start=start,
        window_end=end,
        total_observations=10,
        final_observations=10,
        retryable_observations=0,
        observations_with_evidence=10,
        verified=9,
        partially_verified=0,
        failed=1,
        inconclusive=0,
        not_verifiable=0,
        average_confidence=0.95,
        evidence_coverage=1.0,
        finality_ratio=1.0,
        effective_sample_size=10.0,
        weighted_positive_mass=9.0,
        weighted_negative_mass=1.0,
        weighted_unresolved_mass=0.0,
        estimated_success_rate=0.9,
        summary_confidence=0.95,
        minimum_effective_sample_size=5.0,
        evidence_sufficient=True,
        dominant_outcome="verified",
        quality_level=(
            CapabilityLearningQualityLevel.HIGH
        ),
        interpretation=(
            CapabilityLearningInterpretation
            .POSITIVE
        ),
    )


def _trend_report() -> (
    CapabilityLearningTrendReport
):
    historical = _summary(recent=False)
    recent = _summary(recent=True)

    return CapabilityLearningTrendReport(
        capability_id=CAPABILITY_ID,
        provider_id=PROVIDER_ID,
        provider_ref=PROVIDER_REF,
        tenant_id=TENANT_ID,
        action=ACTION,
        historical=historical,
        recent=recent,
        historical_evidence_sufficient=True,
        recent_evidence_sufficient=True,
        comparison_evidence_sufficient=True,
        success_rate_delta=0.0,
        confidence_delta=0.0,
        effective_sample_delta=0.0,
        outcome_distribution_divergence=0.0,
        contradiction_score=0.05,
        stability_score=0.95,
        interpretation_changed=False,
        dominant_outcome_changed=False,
        direct_interpretation_conflict=False,
        trend_direction=(
            CapabilityLearningTrendDirection
            .STABLE
        ),
        stability_level=(
            CapabilityLearningStabilityLevel
            .STABLE
        ),
        advisory_status=(
            CapabilityLearningAdvisoryStatus
            .TRUST
        ),
        explanation=(
            "Stable verified evidence supports "
            "informational planner context."
        ),
    )


def _typed_telemetry(
    session,
) -> PlannerAdvisorySessionTelemetry:
    """
    Uses the same session-metric projection exposed by the planner API.

    This conversion is output-only and never calls planning again.
    """

    metrics = session.metrics

    return PlannerAdvisorySessionTelemetry(
        available=bool(
            metrics.get(
                "advisory_context_available",
                False,
            )
        ),
        injected=bool(
            metrics.get(
                "advisory_context_injected",
                False,
            )
        ),
        fragment_count=int(
            metrics.get(
                "advisory_fragment_count",
                0,
            )
            or 0
        ),
        source_promotion_ids=list(
            metrics.get(
                "advisory_source_promotion_ids",
                [],
            )
            or []
        ),
        informational_only=bool(
            metrics.get(
                "advisory_informational_only",
                True,
            )
        ),
        affects_score=bool(
            metrics.get(
                "advisory_affects_score",
                False,
            )
        ),
        affects_ordering=bool(
            metrics.get(
                "advisory_affects_ordering",
                False,
            )
        ),
        affects_capability_selection=bool(
            metrics.get(
                "advisory_affects_capability_selection",
                False,
            )
        ),
        affects_business_plan=bool(
            metrics.get(
                "advisory_affects_business_plan",
                False,
            )
        ),
        authorizes_execution=bool(
            metrics.get(
                "advisory_authorizes_execution",
                False,
            )
        ),
        bypasses_approval=bool(
            metrics.get(
                "advisory_bypasses_approval",
                False,
            )
        ),
        bypasses_verification=bool(
            metrics.get(
                "advisory_bypasses_verification",
                False,
            )
        ),
    )


def _candidate_without_observation(
    session,
):
    candidate = deepcopy(
        session.selected_candidate
    )

    observation = (
        candidate["metrics"].pop(
            ADVISORY_OBSERVATION_KEY
        )
    )

    return candidate, observation


@pytest.mark.asyncio
async def test_persisted_learning_advisory_reaches_planner_without_influence():
    user_id = uuid4()

    factory = (
        CapabilityLearningInsightCandidateFactory()
    )

    proposed = factory.propose(
        report=_trend_report(),
        proposed_at=NOW,
    )

    approved = factory.review(
        candidate=proposed,
        approved=True,
        reviewed_by_user_id=user_id,
        reason=(
            "Human reviewer approved this "
            "informational advisory."
        ),
        reviewed_at=NOW,
    )

    promotion = (
        CapabilityLearningPromotionFactory
        .promote(
            user_id=user_id,
            candidate=approved,
            created_by_user_id=user_id,
            reason=(
                "Expose approved evidence as "
                "planner context."
            ),
            created_at=NOW,
        )
    )

    async with SessionLocal() as db:
        candidate_repository = (
            CapabilityLearningInsightCandidateRepository(
                db
            )
        )
        promotion_repository = (
            CapabilityLearningInsightPromotionRepository(
                db
            )
        )

        first_revision = await (
            candidate_repository.append_revision(
                user_id=user_id,
                candidate=proposed,
            )
        )
        approved_revision = await (
            candidate_repository.append_revision(
                user_id=user_id,
                candidate=approved,
            )
        )
        promotion_row = await (
            promotion_repository.append_event(
                promotion=promotion,
            )
        )

        assert first_revision.version == 1
        assert approved_revision.version == 2
        assert (
            approved_revision.status
            == "approved"
        )
        assert (
            approved_revision
            .promotion_eligible
            is True
        )
        assert promotion_row.event_version == 1
        assert promotion_row.status == "active"

        advisories = await (
            CapabilityPlannerAdvisoryService(
                db
            )
            .list_for_scope(
                user_id=user_id,
                tenant_id=TENANT_ID,
                capability_id=CAPABILITY_ID,
                provider_id=PROVIDER_ID,
                provider_ref=PROVIDER_REF,
                action=ACTION,
            )
        )

    assert len(advisories) == 1

    advisory = advisories[0]

    assert (
        advisory.provenance.promotion_id
        == promotion.promotion_id
    )
    assert (
        advisory.scope.capability_id
        == CAPABILITY_ID
    )

    structured_context = (
        CapabilityPlannerAdvisoryPolicy()
        .consume(advisories)
    )

    assert (
        structured_context.advisory_count
        == 1
    )
    assert (
        structured_context
        .source_promotion_ids
        == (promotion.promotion_id,)
    )
    assert (
        structured_context
        .informational_only
        is True
    )

    rendered_context = (
        CapabilityPlannerAdvisoryRenderer()
        .render(structured_context)
    )

    assert rendered_context.present is True
    assert rendered_context.text.strip()
    assert (
        rendered_context.payload[
            "source_promotion_ids"
        ]
        == [str(promotion.promotion_id)]
    )
    assert (
        rendered_context.payload["safety"][
            "informational_only"
        ]
        is True
    )
    assert (
        rendered_context.payload["safety"][
            "affects_ranking"
        ]
        is False
    )
    assert (
        rendered_context.payload["safety"][
            "affects_compatibility"
        ]
        is False
    )
    assert (
        rendered_context.payload["safety"][
            "selects_provider"
        ]
        is False
    )
    assert (
        rendered_context.payload["safety"][
            "authorizes_execution"
        ]
        is False
    )
    assert (
        rendered_context.payload["safety"][
            "bypasses_approval"
        ]
        is False
    )
    assert (
        rendered_context.payload["safety"][
            "bypasses_verification"
        ]
        is False
    )

    base_context = (
        build_default_planning_context(
            user_message=GOAL
        )
    )

    injection = (
        PlannerAdvisoryContextInjector()
        .inject(
            context=base_context,
            rendered_contexts=[
                rendered_context
            ],
            enabled=True,
        )
    )

    assert injection.requested is True
    assert injection.injected is True
    assert injection.fragment_count == 1
    assert injection.informational_only is True
    assert injection.affects_ranking is False
    assert (
        injection
        .affects_capability_selection
        is False
    )
    assert (
        injection.affects_compatibility
        is False
    )
    assert (
        injection.authorizes_execution
        is False
    )
    assert injection.bypasses_approval is False
    assert (
        injection.bypasses_verification
        is False
    )

    baseline = (
        PlannerRuntime()
        .plan_goal(
            goal=GOAL,
            user_id=str(user_id),
            tenant_id=TENANT_ID,
        )
    )

    observed = (
        PlannerRuntime()
        .plan_goal(
            goal=GOAL,
            user_id=str(user_id),
            tenant_id=TENANT_ID,
            planning_context=(
                injection.context
            ),
        )
    )

    (
        baseline_candidate,
        baseline_observation,
    ) = _candidate_without_observation(
        baseline
    )

    (
        observed_candidate,
        observed_observation,
    ) = _candidate_without_observation(
        observed
    )

    # The only selected-candidate difference is
    # informational observation metadata.
    assert (
        baseline_candidate
        == observed_candidate
    )

    assert (
        baseline_observation["injected"]
        is False
    )
    assert (
        observed_observation["injected"]
        is True
    )
    assert (
        observed_observation[
            "fragment_count"
        ]
        == 1
    )
    assert (
        observed_observation[
            "source_promotion_ids"
        ]
        == [str(promotion.promotion_id)]
    )

    # No ranking or plan-selection influence.
    assert (
        baseline.selected_candidate["id"]
        == observed.selected_candidate["id"]
    )
    assert (
        baseline.selected_candidate["score"]
        == observed.selected_candidate["score"]
    )
    assert (
        baseline.selected_candidate[
            "metrics"
        ]["selected_capability"]
        == observed.selected_candidate[
            "metrics"
        ]["selected_capability"]
    )

    # No BusinessPlan, verification, repair,
    # or compilation influence.
    assert (
        baseline.business_plan
        == observed.business_plan
    )
    assert (
        baseline.verification_result
        == observed.verification_result
    )
    assert (
        baseline.repair_result
        == observed.repair_result
    )
    assert (
        baseline.compilation
        == observed.compilation
    )

    # Session telemetry sees the persisted
    # promotion but grants no authority.
    assert (
        observed.metrics[
            "advisory_context_available"
        ]
        is True
    )
    assert (
        observed.metrics[
            "advisory_context_injected"
        ]
        is True
    )
    assert (
        observed.metrics[
            "advisory_fragment_count"
        ]
        == 1
    )
    assert (
        observed.metrics[
            "advisory_source_promotion_ids"
        ]
        == [str(promotion.promotion_id)]
    )
    assert (
        observed.metrics[
            "advisory_affects_score"
        ]
        is False
    )
    assert (
        observed.metrics[
            "advisory_affects_ordering"
        ]
        is False
    )
    assert (
        observed.metrics[
            "advisory_affects_capability_selection"
        ]
        is False
    )
    assert (
        observed.metrics[
            "advisory_affects_business_plan"
        ]
        is False
    )
    assert (
        observed.metrics[
            "advisory_authorizes_execution"
        ]
        is False
    )
    assert (
        observed.metrics[
            "advisory_bypasses_approval"
        ]
        is False
    )
    assert (
        observed.metrics[
            "advisory_bypasses_verification"
        ]
        is False
    )

    advisory_events = [
        event
        for event in observed.events
        if event.type
        == PLANNER_ADVISORY_OBSERVED_EVENT
    ]

    assert len(advisory_events) == 1
    assert (
        advisory_events[0].payload[
            "source_promotion_ids"
        ]
        == [str(promotion.promotion_id)]
    )

    typed = _typed_telemetry(observed)

    assert typed.available is True
    assert typed.injected is True
    assert typed.fragment_count == 1
    assert typed.source_promotion_ids == (
        str(promotion.promotion_id),
    )
    assert typed.informational_only is True
    assert typed.affects_score is False
    assert typed.affects_ordering is False
    assert (
        typed.affects_capability_selection
        is False
    )
    assert typed.affects_business_plan is False
    assert typed.authorizes_execution is False
    assert typed.bypasses_approval is False
    assert typed.bypasses_verification is False
