from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.runtime.capabilities.execution.learning import (
    CapabilityLearningAdvisoryStatus,
    CapabilityLearningApprovalStatus,
    CapabilityLearningCandidateStatus,
    CapabilityLearningInsightCandidateFactory,
    CapabilityLearningInterpretation,
    CapabilityLearningPromotionEventType,
    CapabilityLearningPromotionFactory,
    CapabilityLearningPromotionStatus,
    CapabilityLearningQualityLevel,
    CapabilityLearningStabilityLevel,
    CapabilityLearningSummary,
    CapabilityLearningTrendDirection,
    CapabilityLearningTrendReport,
)


NOW = datetime(
    2026,
    7,
    19,
    12,
    0,
    tzinfo=timezone.utc,
)


def _summary(*, recent: bool):
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
        capability_id="capability.promotion.test",
        provider_id="provider-a",
        provider_ref="provider-a.action",
        tenant_id="tenant-a",
        action="execute",
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


def _approved_candidate():
    historical = _summary(recent=False)
    recent = _summary(recent=True)

    report = CapabilityLearningTrendReport(
        capability_id=historical.capability_id,
        provider_id=historical.provider_id,
        provider_ref=historical.provider_ref,
        tenant_id=historical.tenant_id,
        action=historical.action,
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
            CapabilityLearningTrendDirection.STABLE
        ),
        stability_level=(
            CapabilityLearningStabilityLevel.STABLE
        ),
        advisory_status=(
            CapabilityLearningAdvisoryStatus.TRUST
        ),
        explanation="Stable evidence.",
    )

    factory = (
        CapabilityLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=report,
        proposed_at=NOW,
    )

    return factory.review(
        candidate=candidate,
        approved=True,
        reviewed_by_user_id=uuid4(),
        reason="Confirmed.",
        reviewed_at=NOW,
    )


def test_approved_candidate_can_be_promoted():
    user_id = uuid4()
    candidate = _approved_candidate()

    promotion = (
        CapabilityLearningPromotionFactory
        .promote(
            user_id=user_id,
            candidate=candidate,
            created_by_user_id=user_id,
            reason="Enable advisory use.",
            created_at=NOW,
        )
    )

    assert promotion.event_version == 1
    assert promotion.event_type == (
        CapabilityLearningPromotionEventType
        .PROMOTED
    )
    assert promotion.status == (
        CapabilityLearningPromotionStatus
        .ACTIVE
    )
    assert promotion.candidate_id == (
        candidate.candidate_id
    )
    assert promotion.candidate_version == 2


def test_active_promotion_can_be_revoked_once():
    user_id = uuid4()
    current = (
        CapabilityLearningPromotionFactory
        .promote(
            user_id=user_id,
            candidate=_approved_candidate(),
            created_by_user_id=user_id,
            reason="Enable advisory use.",
            created_at=NOW,
        )
    )

    revoked = (
        CapabilityLearningPromotionFactory
        .revoke(
            current=current,
            created_by_user_id=user_id,
            reason="Evidence no longer trusted.",
            created_at=NOW,
        )
    )

    assert revoked.promotion_id == (
        current.promotion_id
    )
    assert revoked.event_version == 2
    assert revoked.event_type == (
        CapabilityLearningPromotionEventType
        .REVOKED
    )
    assert revoked.status == (
        CapabilityLearningPromotionStatus
        .REVOKED
    )

    with pytest.raises(
        ValueError,
        match="Only an active promotion",
    ):
        (
            CapabilityLearningPromotionFactory
            .revoke(
                current=revoked,
                created_by_user_id=user_id,
                reason="Second revocation.",
            )
        )


@pytest.mark.parametrize(
    "update",
    [
        {
            "status": (
                CapabilityLearningCandidateStatus
                .VALIDATED
            ),
        },
        {
            "approval_status": (
                CapabilityLearningApprovalStatus
                .PENDING
            ),
        },
        {"promotion_eligible": False},
        {
            "blocking_reasons": (
                "manual_block",
            )
        },
    ],
)
def test_ineligible_candidate_cannot_be_promoted(
    update,
):
    candidate = (
        _approved_candidate().model_copy(
            update=update
        )
    )

    with pytest.raises(ValueError):
        (
            CapabilityLearningPromotionFactory
            .promote(
                user_id=uuid4(),
                candidate=candidate,
                created_by_user_id=uuid4(),
                reason="Invalid promotion.",
            )
        )
