from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.runtime.capabilities.execution.learning import (
    CapabilityLearningAdvisoryStatus,
    CapabilityLearningInterpretation,
    CapabilityLearningQualityLevel,
    CapabilityLearningStabilityLevel,
    CapabilityLearningSummary,
    CapabilityLearningTrendAnalyzer,
    CapabilityLearningTrendDirection,
    CapabilityLearningTrendPolicy,
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
    success_rate: float,
    confidence: float = 1.0,
    sufficient: bool = True,
    interpretation: (
        CapabilityLearningInterpretation
    ) = CapabilityLearningInterpretation.POSITIVE,
    dominant_outcome: str = "verified",
    verified: int = 8,
    failed: int = 2,
    partially_verified: int = 0,
    inconclusive: int = 0,
    not_verifiable: int = 0,
    capability_id: str = "ecommerce.orders.manage",
    provider_id: str | None = "shopify",
    provider_ref: str | None = (
        "shopify.order_action"
    ),
    tenant_id: str | None = "tenant-a",
    action: str | None = "refund",
):
    total = (
        verified
        + failed
        + partially_verified
        + inconclusive
        + not_verifiable
    )

    if recent:
        window_start = NOW - timedelta(days=7)
        window_end = NOW
    else:
        window_start = NOW - timedelta(days=14)
        window_end = NOW - timedelta(days=7)

    effective_sample = (
        float(total)
        if sufficient
        else 1.0
    )

    return CapabilityLearningSummary(
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
        tenant_id=tenant_id,
        action=action,
        window_start=window_start,
        window_end=window_end,
        total_observations=total,
        final_observations=total,
        retryable_observations=0,
        observations_with_evidence=total,
        verified=verified,
        partially_verified=(
            partially_verified
        ),
        failed=failed,
        inconclusive=inconclusive,
        not_verifiable=not_verifiable,
        average_confidence=confidence,
        evidence_coverage=1.0,
        finality_ratio=1.0,
        effective_sample_size=(
            effective_sample
        ),
        weighted_positive_mass=(
            success_rate * effective_sample
        ),
        weighted_negative_mass=(
            (1.0 - success_rate)
            * effective_sample
        ),
        weighted_unresolved_mass=0.0,
        estimated_success_rate=success_rate,
        summary_confidence=confidence,
        minimum_effective_sample_size=5.0,
        evidence_sufficient=sufficient,
        dominant_outcome=dominant_outcome,
        quality_level=(
            CapabilityLearningQualityLevel.HIGH
            if sufficient
            else CapabilityLearningQualityLevel
            .INSUFFICIENT
        ),
        interpretation=interpretation,
    )


def test_identical_windows_are_stable_and_trusted():
    report = (
        CapabilityLearningTrendAnalyzer()
        .compare(
            historical=summary(
                recent=False,
                success_rate=0.8,
            ),
            recent=summary(
                recent=True,
                success_rate=0.8,
            ),
        )
    )

    assert report.success_rate_delta == 0.0
    assert (
        report.outcome_distribution_divergence
        == 0.0
    )
    assert report.contradiction_score == 0.0
    assert report.stability_score == 1.0
    assert report.trend_direction == (
        CapabilityLearningTrendDirection.STABLE
    )
    assert report.stability_level == (
        CapabilityLearningStabilityLevel.STABLE
    )
    assert report.advisory_status == (
        CapabilityLearningAdvisoryStatus.TRUST
    )


def test_meaningful_success_increase_is_improving():
    report = (
        CapabilityLearningTrendAnalyzer()
        .compare(
            historical=summary(
                recent=False,
                success_rate=0.60,
                verified=6,
                failed=4,
                interpretation=(
                    CapabilityLearningInterpretation
                    .MIXED
                ),
            ),
            recent=summary(
                recent=True,
                success_rate=0.85,
                verified=9,
                failed=1,
            ),
        )
    )

    assert report.success_rate_delta == (
        pytest.approx(0.25)
    )
    assert report.trend_direction == (
        CapabilityLearningTrendDirection
        .IMPROVING
    )
    assert report.advisory_status == (
        CapabilityLearningAdvisoryStatus.WATCH
    )


def test_meaningful_success_decrease_is_declining():
    report = (
        CapabilityLearningTrendAnalyzer()
        .compare(
            historical=summary(
                recent=False,
                success_rate=0.90,
                verified=9,
                failed=1,
            ),
            recent=summary(
                recent=True,
                success_rate=0.50,
                verified=5,
                failed=5,
                interpretation=(
                    CapabilityLearningInterpretation
                    .MIXED
                ),
                dominant_outcome="failed",
            ),
        )
    )

    assert report.success_rate_delta == (
        pytest.approx(-0.40)
    )
    assert report.trend_direction == (
        CapabilityLearningTrendDirection
        .DECLINING
    )
    assert report.advisory_status in {
        CapabilityLearningAdvisoryStatus.WATCH,
        CapabilityLearningAdvisoryStatus.REVIEW,
    }


def test_positive_to_negative_is_direct_contradiction():
    report = (
        CapabilityLearningTrendAnalyzer()
        .compare(
            historical=summary(
                recent=False,
                success_rate=0.90,
                verified=9,
                failed=1,
                interpretation=(
                    CapabilityLearningInterpretation
                    .POSITIVE
                ),
                dominant_outcome="verified",
            ),
            recent=summary(
                recent=True,
                success_rate=0.10,
                verified=1,
                failed=9,
                interpretation=(
                    CapabilityLearningInterpretation
                    .NEGATIVE
                ),
                dominant_outcome="failed",
            ),
        )
    )

    assert (
        report.direct_interpretation_conflict
        is True
    )
    assert (
        report.dominant_outcome_changed
        is True
    )
    assert report.contradiction_score == 1.0
    assert report.trend_direction == (
        CapabilityLearningTrendDirection
        .CONTRADICTORY
    )
    assert report.stability_level == (
        CapabilityLearningStabilityLevel
        .UNSTABLE
    )
    assert report.advisory_status == (
        CapabilityLearningAdvisoryStatus.REVIEW
    )


def test_low_confidence_conflict_has_reduced_contradiction():
    report = (
        CapabilityLearningTrendAnalyzer()
        .compare(
            historical=summary(
                recent=False,
                success_rate=0.90,
                confidence=0.30,
                interpretation=(
                    CapabilityLearningInterpretation
                    .POSITIVE
                ),
            ),
            recent=summary(
                recent=True,
                success_rate=0.10,
                confidence=0.30,
                verified=1,
                failed=9,
                interpretation=(
                    CapabilityLearningInterpretation
                    .NEGATIVE
                ),
                dominant_outcome="failed",
            ),
        )
    )

    assert report.contradiction_score == (
        pytest.approx(0.30)
    )
    assert report.trend_direction == (
        CapabilityLearningTrendDirection
        .DECLINING
    )


def test_insufficient_window_blocks_trend_conclusion():
    report = (
        CapabilityLearningTrendAnalyzer()
        .compare(
            historical=summary(
                recent=False,
                success_rate=0.90,
                sufficient=False,
            ),
            recent=summary(
                recent=True,
                success_rate=0.10,
                verified=1,
                failed=9,
                interpretation=(
                    CapabilityLearningInterpretation
                    .NEGATIVE
                ),
                dominant_outcome="failed",
            ),
        )
    )

    assert (
        report.comparison_evidence_sufficient
        is False
    )
    assert report.stability_score == 0.0
    assert report.trend_direction == (
        CapabilityLearningTrendDirection
        .INSUFFICIENT_EVIDENCE
    )
    assert report.stability_level == (
        CapabilityLearningStabilityLevel
        .INSUFFICIENT
    )
    assert report.advisory_status == (
        CapabilityLearningAdvisoryStatus
        .INSUFFICIENT_EVIDENCE
    )


def test_outcome_distribution_divergence_is_bounded():
    report = (
        CapabilityLearningTrendAnalyzer()
        .compare(
            historical=summary(
                recent=False,
                success_rate=1.0,
                verified=10,
                failed=0,
            ),
            recent=summary(
                recent=True,
                success_rate=0.0,
                verified=0,
                failed=10,
                interpretation=(
                    CapabilityLearningInterpretation
                    .NEGATIVE
                ),
                dominant_outcome="failed",
            ),
        )
    )

    assert (
        report.outcome_distribution_divergence
        == 1.0
    )


def test_scope_mismatch_is_rejected():
    with pytest.raises(
        ValueError,
        match="same scope",
    ):
        (
            CapabilityLearningTrendAnalyzer()
            .compare(
                historical=summary(
                    recent=False,
                    success_rate=0.8,
                    action="refund",
                ),
                recent=summary(
                    recent=True,
                    success_rate=0.8,
                    action="cancel",
                ),
            )
        )


def test_overlapping_windows_are_rejected():
    historical = summary(
        recent=False,
        success_rate=0.8,
    )
    recent = summary(
        recent=True,
        success_rate=0.8,
    ).model_copy(
        update={
            "window_start": (
                historical.window_end
                - timedelta(hours=1)
            )
        }
    )

    with pytest.raises(
        ValueError,
        match="must not overlap",
    ):
        (
            CapabilityLearningTrendAnalyzer()
            .compare(
                historical=historical,
                recent=recent,
            )
        )


def test_unbounded_windows_are_rejected():
    historical = summary(
        recent=False,
        success_rate=0.8,
    ).model_copy(
        update={"window_start": None}
    )

    with pytest.raises(
        ValueError,
        match="bounded windows",
    ):
        (
            CapabilityLearningTrendAnalyzer()
            .compare(
                historical=historical,
                recent=summary(
                    recent=True,
                    success_rate=0.8,
                ),
            )
        )


@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        ("meaningful_success_delta", -0.1),
        ("contradiction_threshold", 1.1),
        ("stable_score_threshold", 1.1),
        ("success_delta_weight", -0.1),
    ],
)
def test_invalid_trend_policy_values_are_rejected(
    keyword,
    value,
):
    with pytest.raises(ValueError):
        CapabilityLearningTrendPolicy(
            **{keyword: value}
        )


def test_trend_weights_must_sum_to_one():
    with pytest.raises(
        ValueError,
        match="weights must sum to 1.0",
    ):
        CapabilityLearningTrendPolicy(
            success_delta_weight=0.5,
            distribution_divergence_weight=0.5,
            contradiction_weight=0.5,
        )
