from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.runtime.learning import (
    BusinessLearningAdvisoryStatus,
    BusinessLearningEvidenceLevel,
    BusinessLearningInterpretation,
    BusinessLearningStabilityLevel,
    BusinessLearningSummary,
    BusinessLearningTrendAnalyzer,
    BusinessLearningTrendDirection,
    BusinessLearningTrendPolicy,
)


NOW = datetime(
    2026,
    8,
    2,
    12,
    0,
    tzinfo=timezone.utc,
)


def summary(
    *,
    recent: bool,
    success_rate: float,
    failure_rate: float,
    confidence: float = 1.0,
    sufficient: bool = True,
    interpretation: (
        BusinessLearningInterpretation
    ) = BusinessLearningInterpretation.POSITIVE,
    dominant_result: str = "achieved",
    achieved: int = 8,
    failed: int = 2,
    partially_achieved: int = 0,
    progressing: int = 0,
    intentionally_not_executed: int = 0,
    inconclusive: int = 0,
    tenant_id: str | None = "tenant-a",
    objective_namespace: str = (
        "customer_service.support"
    ),
    objective_type: str = "multi_operation",
    decision: str = "approved",
):
    total = (
        achieved
        + failed
        + partially_achieved
        + progressing
        + intentionally_not_executed
        + inconclusive
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

    return BusinessLearningSummary(
        tenant_id=tenant_id,
        objective_namespace=objective_namespace,
        objective_type=objective_type,
        decision=decision,
        window_start=window_start,
        window_end=window_end,
        total_observations=total,
        final_observations=total,
        retryable_observations=0,
        observations_with_evidence=total,
        achieved=achieved,
        partially_achieved=partially_achieved,
        progressing=progressing,
        failed=failed,
        intentionally_not_executed=(
            intentionally_not_executed
        ),
        inconclusive=inconclusive,
        total_operations=total,
        achieved_operations=achieved,
        failed_operations=failed,
        pending_operations=progressing,
        unknown_operations=inconclusive,
        not_executed_operations=(
            intentionally_not_executed
        ),
        average_confidence=confidence,
        evidence_coverage=1.0,
        finality_ratio=1.0,
        effective_sample_size=effective_sample,
        weighted_success_mass=(
            success_rate * effective_sample
        ),
        weighted_failure_mass=(
            failure_rate * effective_sample
        ),
        weighted_unresolved_mass=0.0,
        weighted_not_executed_mass=0.0,
        estimated_success_rate=success_rate,
        estimated_failure_rate=failure_rate,
        summary_confidence=confidence,
        minimum_effective_sample_size=5.0,
        evidence_sufficient=sufficient,
        dominant_result=dominant_result,
        evidence_level=(
            BusinessLearningEvidenceLevel.HIGH
            if sufficient
            else BusinessLearningEvidenceLevel
            .INSUFFICIENT
        ),
        interpretation=interpretation,
    )


def test_identical_business_windows_are_stable():
    report = BusinessLearningTrendAnalyzer().compare(
        historical=summary(
            recent=False,
            success_rate=0.8,
            failure_rate=0.2,
        ),
        recent=summary(
            recent=True,
            success_rate=0.8,
            failure_rate=0.2,
        ),
    )

    assert report.success_rate_delta == 0.0
    assert report.failure_rate_delta == 0.0
    assert (
        report.result_distribution_divergence
        == 0.0
    )
    assert report.stability_score == 1.0
    assert report.trend_direction == (
        BusinessLearningTrendDirection.STABLE
    )
    assert report.stability_level == (
        BusinessLearningStabilityLevel.STABLE
    )
    assert report.advisory_status == (
        BusinessLearningAdvisoryStatus.TRUST
    )


def test_success_increase_is_improving():
    report = BusinessLearningTrendAnalyzer().compare(
        historical=summary(
            recent=False,
            success_rate=0.5,
            failure_rate=0.5,
            achieved=5,
            failed=5,
            interpretation=(
                BusinessLearningInterpretation.MIXED
            ),
        ),
        recent=summary(
            recent=True,
            success_rate=0.9,
            failure_rate=0.1,
            achieved=9,
            failed=1,
        ),
    )

    assert report.success_rate_delta == (
        pytest.approx(0.4)
    )
    assert report.failure_rate_delta == (
        pytest.approx(-0.4)
    )
    assert report.trend_direction == (
        BusinessLearningTrendDirection
        .IMPROVING
    )


def test_failure_increase_is_declining():
    report = BusinessLearningTrendAnalyzer().compare(
        historical=summary(
            recent=False,
            success_rate=0.9,
            failure_rate=0.1,
            achieved=9,
            failed=1,
        ),
        recent=summary(
            recent=True,
            success_rate=0.5,
            failure_rate=0.5,
            achieved=5,
            failed=5,
            interpretation=(
                BusinessLearningInterpretation.MIXED
            ),
            dominant_result="failed",
        ),
    )

    assert report.trend_direction == (
        BusinessLearningTrendDirection
        .DECLINING
    )


def test_positive_to_negative_is_contradictory():
    report = BusinessLearningTrendAnalyzer().compare(
        historical=summary(
            recent=False,
            success_rate=0.9,
            failure_rate=0.1,
            achieved=9,
            failed=1,
            dominant_result="achieved",
        ),
        recent=summary(
            recent=True,
            success_rate=0.1,
            failure_rate=0.9,
            achieved=1,
            failed=9,
            interpretation=(
                BusinessLearningInterpretation
                .NEGATIVE
            ),
            dominant_result="failed",
        ),
    )

    assert (
        report.direct_interpretation_conflict
        is True
    )
    assert report.dominant_result_changed is True
    assert report.contradiction_score == 1.0
    assert report.trend_direction == (
        BusinessLearningTrendDirection
        .CONTRADICTORY
    )
    assert report.stability_level == (
        BusinessLearningStabilityLevel
        .UNSTABLE
    )
    assert report.advisory_status == (
        BusinessLearningAdvisoryStatus.REVIEW
    )


def test_low_confidence_conflict_is_downweighted():
    report = BusinessLearningTrendAnalyzer().compare(
        historical=summary(
            recent=False,
            success_rate=0.9,
            failure_rate=0.1,
            confidence=0.3,
        ),
        recent=summary(
            recent=True,
            success_rate=0.1,
            failure_rate=0.9,
            confidence=0.3,
            achieved=1,
            failed=9,
            interpretation=(
                BusinessLearningInterpretation
                .NEGATIVE
            ),
            dominant_result="failed",
        ),
    )

    assert report.contradiction_score == (
        pytest.approx(0.3)
    )
    assert report.trend_direction == (
        BusinessLearningTrendDirection
        .DECLINING
    )


def test_insufficient_window_blocks_conclusion():
    report = BusinessLearningTrendAnalyzer().compare(
        historical=summary(
            recent=False,
            success_rate=0.9,
            failure_rate=0.1,
            sufficient=False,
        ),
        recent=summary(
            recent=True,
            success_rate=0.1,
            failure_rate=0.9,
            achieved=1,
            failed=9,
            interpretation=(
                BusinessLearningInterpretation
                .NEGATIVE
            ),
            dominant_result="failed",
        ),
    )

    assert (
        report.comparison_evidence_sufficient
        is False
    )
    assert report.stability_score == 0.0
    assert report.trend_direction == (
        BusinessLearningTrendDirection
        .INSUFFICIENT_EVIDENCE
    )
    assert report.stability_level == (
        BusinessLearningStabilityLevel
        .INSUFFICIENT
    )


def test_scope_mismatch_is_rejected():
    with pytest.raises(
        ValueError,
        match="same scope",
    ):
        BusinessLearningTrendAnalyzer().compare(
            historical=summary(
                recent=False,
                success_rate=0.8,
                failure_rate=0.2,
                decision="approved",
            ),
            recent=summary(
                recent=True,
                success_rate=0.8,
                failure_rate=0.2,
                decision="rejected",
            ),
        )


def test_non_adjacent_windows_are_rejected():
    historical = summary(
        recent=False,
        success_rate=0.8,
        failure_rate=0.2,
    )

    recent = summary(
        recent=True,
        success_rate=0.8,
        failure_rate=0.2,
    ).model_copy(
        update={
            "window_start": (
                historical.window_end
                + timedelta(hours=1)
            )
        }
    )

    with pytest.raises(
        ValueError,
        match="adjacent",
    ):
        BusinessLearningTrendAnalyzer().compare(
            historical=historical,
            recent=recent,
        )


def test_unbounded_windows_are_rejected():
    historical = summary(
        recent=False,
        success_rate=0.8,
        failure_rate=0.2,
    ).model_copy(
        update={"window_start": None}
    )

    with pytest.raises(
        ValueError,
        match="bounded windows",
    ):
        BusinessLearningTrendAnalyzer().compare(
            historical=historical,
            recent=summary(
                recent=True,
                success_rate=0.8,
                failure_rate=0.2,
            ),
        )


@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        ("meaningful_success_delta", -0.1),
        ("meaningful_failure_delta", 1.1),
        ("contradiction_threshold", 1.1),
        ("success_delta_weight", -0.1),
    ],
)
def test_invalid_trend_policy_values_are_rejected(
    keyword,
    value,
):
    with pytest.raises(ValueError):
        BusinessLearningTrendPolicy(
            **{keyword: value}
        )


def test_trend_weights_must_sum_to_one():
    with pytest.raises(
        ValueError,
        match="weights must sum to 1.0",
    ):
        BusinessLearningTrendPolicy(
            success_delta_weight=0.5,
            failure_delta_weight=0.5,
            distribution_divergence_weight=0.5,
            contradiction_weight=0.5,
        )
