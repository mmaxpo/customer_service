from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.runtime.capabilities.execution.learning import (
    CapabilityLearningAdvisoryStatus,
    CapabilityLearningApprovalStatus,
    CapabilityLearningCandidateStatus,
    CapabilityLearningInsightCandidateFactory,
    CapabilityLearningInsightKind,
    CapabilityLearningInsightPolicy,
    CapabilityLearningInterpretation,
    CapabilityLearningPromotionTarget,
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


def summary(
    *,
    recent: bool,
    interpretation=(
        CapabilityLearningInterpretation
        .POSITIVE
    ),
    confidence: float = 0.95,
    quality=CapabilityLearningQualityLevel.HIGH,
    sufficient: bool = True,
    success_rate: float = 0.90,
):
    if recent:
        start = NOW - timedelta(days=7)
        end = NOW
    else:
        start = NOW - timedelta(days=14)
        end = NOW - timedelta(days=7)

    return CapabilityLearningSummary(
        capability_id="ecommerce.orders.manage",
        provider_id="shopify",
        provider_ref="shopify.order_action",
        tenant_id="tenant-a",
        action="refund",
        window_start=start,
        window_end=end,
        total_observations=10,
        final_observations=10,
        retryable_observations=0,
        observations_with_evidence=10,
        verified=(
            9
            if interpretation
            == CapabilityLearningInterpretation
            .POSITIVE
            else 1
        ),
        partially_verified=0,
        failed=(
            1
            if interpretation
            == CapabilityLearningInterpretation
            .POSITIVE
            else 9
        ),
        inconclusive=0,
        not_verifiable=0,
        average_confidence=confidence,
        evidence_coverage=1.0,
        finality_ratio=1.0,
        effective_sample_size=10.0,
        weighted_positive_mass=(
            success_rate * 10
        ),
        weighted_negative_mass=(
            (1.0 - success_rate) * 10
        ),
        weighted_unresolved_mass=0.0,
        estimated_success_rate=success_rate,
        summary_confidence=confidence,
        minimum_effective_sample_size=5.0,
        evidence_sufficient=sufficient,
        dominant_outcome=(
            "verified"
            if interpretation
            == CapabilityLearningInterpretation
            .POSITIVE
            else "failed"
        ),
        quality_level=quality,
        interpretation=interpretation,
    )


def trusted_report(
    *,
    interpretation=(
        CapabilityLearningInterpretation
        .POSITIVE
    ),
    contradiction_score: float = 0.05,
    advisory_status=(
        CapabilityLearningAdvisoryStatus.TRUST
    ),
    stability_level=(
        CapabilityLearningStabilityLevel.STABLE
    ),
    trend_direction=(
        CapabilityLearningTrendDirection.STABLE
    ),
    confidence: float = 0.95,
    sufficient: bool = True,
):
    success_rate = (
        0.90
        if interpretation
        == CapabilityLearningInterpretation
        .POSITIVE
        else 0.10
    )

    historical = summary(
        recent=False,
        interpretation=interpretation,
        confidence=confidence,
        sufficient=sufficient,
        success_rate=success_rate,
    )
    recent = summary(
        recent=True,
        interpretation=interpretation,
        confidence=confidence,
        sufficient=sufficient,
        success_rate=success_rate,
    )

    return CapabilityLearningTrendReport(
        capability_id=historical.capability_id,
        provider_id=historical.provider_id,
        provider_ref=historical.provider_ref,
        tenant_id=historical.tenant_id,
        action=historical.action,
        historical=historical,
        recent=recent,
        historical_evidence_sufficient=(
            sufficient
        ),
        recent_evidence_sufficient=(
            sufficient
        ),
        comparison_evidence_sufficient=(
            sufficient
        ),
        success_rate_delta=0.0,
        confidence_delta=0.0,
        effective_sample_delta=0.0,
        outcome_distribution_divergence=0.0,
        contradiction_score=(
            contradiction_score
        ),
        stability_score=0.95,
        interpretation_changed=False,
        dominant_outcome_changed=False,
        direct_interpretation_conflict=False,
        trend_direction=trend_direction,
        stability_level=stability_level,
        advisory_status=advisory_status,
        explanation="Stable trusted evidence.",
    )


def test_trusted_positive_pattern_creates_validated_candidate():
    candidate = (
        CapabilityLearningInsightCandidateFactory()
        .propose(
            report=trusted_report()
        )
    )

    assert candidate.kind == (
        CapabilityLearningInsightKind
        .POSITIVE_OUTCOME_PATTERN
    )
    assert candidate.validation_passed is True
    assert candidate.status == (
        CapabilityLearningCandidateStatus
        .VALIDATED
    )
    assert candidate.approval_status == (
        CapabilityLearningApprovalStatus
        .PENDING
    )
    assert candidate.promotion_eligible is False
    assert candidate.blocking_reasons == (
        "explicit_approval_required",
    )
    assert len(
        candidate
        .evidence
        .evidence_fingerprint
    ) == 64


def test_trusted_negative_pattern_creates_warning_candidate():
    candidate = (
        CapabilityLearningInsightCandidateFactory()
        .propose(
            report=trusted_report(
                interpretation=(
                    CapabilityLearningInterpretation
                    .NEGATIVE
                )
            ),
            promotion_target=(
                CapabilityLearningPromotionTarget
                .OPERATOR_GUIDANCE
            ),
        )
    )

    assert candidate.kind == (
        CapabilityLearningInsightKind
        .NEGATIVE_OUTCOME_PATTERN
    )
    assert "warning" in (
        candidate.recommended_behavior
    )
    assert candidate.validation_passed is True


def test_evidence_fingerprint_is_deterministic():
    report = trusted_report()
    factory = (
        CapabilityLearningInsightCandidateFactory()
    )

    first = factory.propose(report=report)
    second = factory.propose(report=report)

    assert (
        first.evidence.evidence_fingerprint
        == second.evidence.evidence_fingerprint
    )
    assert first.candidate_id != second.candidate_id


def test_untrusted_trend_blocks_candidate():
    candidate = (
        CapabilityLearningInsightCandidateFactory()
        .propose(
            report=trusted_report(
                advisory_status=(
                    CapabilityLearningAdvisoryStatus
                    .WATCH
                )
            )
        )
    )

    assert candidate.validation_passed is False
    assert candidate.status == (
        CapabilityLearningCandidateStatus
        .BLOCKED
    )
    assert "advisory_status_trusted" in (
        candidate.blocking_reasons
    )


def test_high_contradiction_blocks_candidate():
    candidate = (
        CapabilityLearningInsightCandidateFactory()
        .propose(
            report=trusted_report(
                contradiction_score=0.50
            )
        )
    )

    assert candidate.validation_passed is False
    assert (
        "contradiction_within_limit"
        in candidate.blocking_reasons
    )


def test_unstable_pattern_blocks_candidate():
    candidate = (
        CapabilityLearningInsightCandidateFactory()
        .propose(
            report=trusted_report(
                advisory_status=(
                    CapabilityLearningAdvisoryStatus
                    .REVIEW
                ),
                stability_level=(
                    CapabilityLearningStabilityLevel
                    .UNSTABLE
                ),
                trend_direction=(
                    CapabilityLearningTrendDirection
                    .CONTRADICTORY
                ),
            )
        )
    )

    assert candidate.validation_passed is False
    assert "stable_learning_pattern" in (
        candidate.blocking_reasons
    )


def test_approval_makes_validated_candidate_eligible():
    reviewer_id = uuid4()
    factory = (
        CapabilityLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=trusted_report()
    )

    approved = factory.review(
        candidate=candidate,
        approved=True,
        reviewed_by_user_id=reviewer_id,
        reason="Evidence manually confirmed.",
        reviewed_at=NOW,
    )

    assert approved.candidate_id == (
        candidate.candidate_id
    )
    assert approved.candidate_version == 2
    assert approved.status == (
        CapabilityLearningCandidateStatus
        .APPROVED
    )
    assert approved.approval_status == (
        CapabilityLearningApprovalStatus
        .APPROVED
    )
    assert approved.promotion_eligible is True
    assert approved.blocking_reasons == ()
    assert approved.reviewed_by_user_id == (
        reviewer_id
    )


def test_rejection_permanently_blocks_current_revision():
    factory = (
        CapabilityLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=trusted_report()
    )

    rejected = factory.review(
        candidate=candidate,
        approved=False,
        reviewed_by_user_id=uuid4(),
        reason="Scope is too narrow.",
    )

    assert rejected.status == (
        CapabilityLearningCandidateStatus
        .REJECTED
    )
    assert rejected.approval_status == (
        CapabilityLearningApprovalStatus
        .REJECTED
    )
    assert rejected.promotion_eligible is False
    assert rejected.blocking_reasons == (
        "approval_rejected",
    )


def test_blocked_candidate_cannot_be_reviewed():
    factory = (
        CapabilityLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=trusted_report(
            advisory_status=(
                CapabilityLearningAdvisoryStatus
                .WATCH
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="Only validated candidates",
    ):
        factory.review(
            candidate=candidate,
            approved=True,
            reviewed_by_user_id=uuid4(),
            reason="Invalid approval attempt.",
        )


def test_mixed_interpretation_cannot_create_candidate():
    report = trusted_report().model_copy(
        update={
            "recent": summary(
                recent=True,
                interpretation=(
                    CapabilityLearningInterpretation
                    .MIXED
                ),
                success_rate=0.50,
            )
        }
    )

    with pytest.raises(
        ValueError,
        match="Only positive or negative",
    ):
        (
            CapabilityLearningInsightCandidateFactory()
            .propose(report=report)
        )


@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        (
            "minimum_summary_confidence",
            -0.1,
        ),
        (
            "maximum_contradiction_score",
            1.1,
        ),
    ],
)
def test_invalid_insight_policy_values_are_rejected(
    keyword,
    value,
):
    with pytest.raises(ValueError):
        CapabilityLearningInsightPolicy(
            **{keyword: value}
        )
