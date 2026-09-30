from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.runtime.learning import (
    BusinessLearningAdvisoryStatus,
    BusinessLearningApprovalStatus,
    BusinessLearningCandidateStatus,
    BusinessLearningEvidenceLevel,
    BusinessLearningInsightCandidateFactory,
    BusinessLearningInsightKind,
    BusinessLearningInsightPolicy,
    BusinessLearningInterpretation,
    BusinessLearningStabilityLevel,
    BusinessLearningSummary,
    BusinessLearningTrendDirection,
    BusinessLearningTrendReport,
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
    interpretation=(
        BusinessLearningInterpretation.POSITIVE
    ),
    confidence: float = 0.95,
    evidence_level=(
        BusinessLearningEvidenceLevel.HIGH
    ),
    sufficient: bool = True,
):
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

    positive = (
        interpretation
        == BusinessLearningInterpretation.POSITIVE
    )

    return BusinessLearningSummary(
        tenant_id="tenant-a",
        objective_namespace=(
            "customer_service.support"
        ),
        objective_type="multi_operation",
        decision="approved",
        window_start=start,
        window_end=end,
        total_observations=10,
        final_observations=10,
        retryable_observations=0,
        observations_with_evidence=10,
        achieved=9 if positive else 1,
        partially_achieved=0,
        progressing=0,
        failed=1 if positive else 9,
        intentionally_not_executed=0,
        inconclusive=0,
        total_operations=10,
        achieved_operations=9 if positive else 1,
        failed_operations=1 if positive else 9,
        pending_operations=0,
        unknown_operations=0,
        not_executed_operations=0,
        average_confidence=confidence,
        evidence_coverage=1.0,
        finality_ratio=1.0,
        effective_sample_size=10.0,
        weighted_success_mass=(
            9.0 if positive else 1.0
        ),
        weighted_failure_mass=(
            1.0 if positive else 9.0
        ),
        weighted_unresolved_mass=0.0,
        weighted_not_executed_mass=0.0,
        estimated_success_rate=(
            0.9 if positive else 0.1
        ),
        estimated_failure_rate=(
            0.1 if positive else 0.9
        ),
        summary_confidence=confidence,
        minimum_effective_sample_size=5.0,
        evidence_sufficient=sufficient,
        dominant_result=(
            "achieved" if positive else "failed"
        ),
        evidence_level=evidence_level,
        interpretation=interpretation,
    )


def trusted_report(
    *,
    interpretation=(
        BusinessLearningInterpretation.POSITIVE
    ),
    confidence: float = 0.95,
    evidence_level=(
        BusinessLearningEvidenceLevel.HIGH
    ),
    sufficient: bool = True,
    contradiction_score: float = 0.05,
    advisory_status=(
        BusinessLearningAdvisoryStatus.TRUST
    ),
    stability_level=(
        BusinessLearningStabilityLevel.STABLE
    ),
    trend_direction=(
        BusinessLearningTrendDirection.STABLE
    ),
):
    historical = summary(
        recent=False,
        interpretation=interpretation,
        confidence=confidence,
        evidence_level=evidence_level,
        sufficient=sufficient,
    )
    recent = summary(
        recent=True,
        interpretation=interpretation,
        confidence=confidence,
        evidence_level=evidence_level,
        sufficient=sufficient,
    )

    return BusinessLearningTrendReport(
        tenant_id=historical.tenant_id,
        objective_namespace=(
            historical.objective_namespace
        ),
        objective_type=historical.objective_type,
        decision=historical.decision,
        historical=historical,
        recent=recent,
        historical_evidence_sufficient=(
            sufficient
        ),
        recent_evidence_sufficient=sufficient,
        comparison_evidence_sufficient=(
            sufficient
        ),
        success_rate_delta=0.0,
        failure_rate_delta=0.0,
        confidence_delta=0.0,
        effective_sample_delta=0.0,
        result_distribution_divergence=0.0,
        contradiction_score=(
            contradiction_score
        ),
        stability_score=0.95,
        interpretation_changed=False,
        dominant_result_changed=False,
        direct_interpretation_conflict=False,
        trend_direction=trend_direction,
        stability_level=stability_level,
        advisory_status=advisory_status,
        explanation="Stable business evidence.",
    )


def test_positive_pattern_creates_validated_candidate():
    candidate = (
        BusinessLearningInsightCandidateFactory()
        .propose(
            report=trusted_report(),
            proposed_at=NOW,
        )
    )

    assert candidate.kind == (
        BusinessLearningInsightKind
        .POSITIVE_BUSINESS_PATTERN
    )
    assert candidate.status == (
        BusinessLearningCandidateStatus.VALIDATED
    )
    assert candidate.validation_passed is True
    assert candidate.approval_status == (
        BusinessLearningApprovalStatus.PENDING
    )
    assert candidate.blocking_reasons == (
        "explicit_approval_required",
    )


def test_negative_pattern_creates_validated_candidate():
    candidate = (
        BusinessLearningInsightCandidateFactory()
        .propose(
            report=trusted_report(
                interpretation=(
                    BusinessLearningInterpretation
                    .NEGATIVE
                )
            ),
            proposed_at=NOW,
        )
    )

    assert candidate.kind == (
        BusinessLearningInsightKind
        .NEGATIVE_BUSINESS_PATTERN
    )
    assert candidate.status == (
        BusinessLearningCandidateStatus.VALIDATED
    )


def test_evidence_fingerprint_is_deterministic():
    report = trusted_report()

    first = (
        BusinessLearningInsightCandidateFactory()
        .propose(
            report=report,
            proposed_at=NOW,
        )
    )
    second = (
        BusinessLearningInsightCandidateFactory()
        .propose(
            report=report,
            proposed_at=NOW,
        )
    )

    assert (
        first.evidence.evidence_fingerprint
        == second.evidence.evidence_fingerprint
    )
    assert (
        len(
            first.evidence.evidence_fingerprint
        )
        == 64
    )


@pytest.mark.parametrize(
    "report",
    [
        trusted_report(
            advisory_status=(
                BusinessLearningAdvisoryStatus.WATCH
            )
        ),
        trusted_report(
            stability_level=(
                BusinessLearningStabilityLevel
                .VARIABLE
            )
        ),
        trusted_report(
            trend_direction=(
                BusinessLearningTrendDirection
                .IMPROVING
            )
        ),
        trusted_report(
            contradiction_score=0.5
        ),
        trusted_report(
            confidence=0.5
        ),
        trusted_report(
            evidence_level=(
                BusinessLearningEvidenceLevel.LOW
            )
        ),
        trusted_report(
            sufficient=False
        ),
    ],
)
def test_unsafe_pattern_is_blocked(
    report,
):
    candidate = (
        BusinessLearningInsightCandidateFactory()
        .propose(
            report=report,
            proposed_at=NOW,
        )
    )

    assert candidate.status == (
        BusinessLearningCandidateStatus.BLOCKED
    )
    assert candidate.validation_passed is False
    assert candidate.blocking_reasons


def test_unsupported_interpretation_is_rejected():
    with pytest.raises(
        ValueError,
        match="positive or negative",
    ):
        (
            BusinessLearningInsightCandidateFactory()
            .propose(
                report=trusted_report().model_copy(
                    update={
                        "recent": summary(
                            recent=True,
                            interpretation=(
                                BusinessLearningInterpretation
                                .MIXED
                            ),
                        )
                    }
                )
            )
        )


def test_approved_review_creates_version_two():
    factory = (
        BusinessLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=trusted_report(),
        proposed_at=NOW,
    )
    reviewer_id = uuid4()

    approved = factory.review(
        candidate=candidate,
        approved=True,
        reviewed_by_user_id=reviewer_id,
        reason="Evidence accepted.",
        reviewed_at=NOW,
    )

    assert approved.candidate_version == 2
    assert approved.status == (
        BusinessLearningCandidateStatus.APPROVED
    )
    assert approved.approval_status == (
        BusinessLearningApprovalStatus.APPROVED
    )
    assert approved.reviewed_by_user_id == (
        reviewer_id
    )
    assert approved.blocking_reasons == ()


def test_rejected_review_records_rejection():
    factory = (
        BusinessLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=trusted_report(),
        proposed_at=NOW,
    )

    rejected = factory.review(
        candidate=candidate,
        approved=False,
        reviewed_by_user_id=uuid4(),
        reason="Evidence not accepted.",
        reviewed_at=NOW,
    )

    assert rejected.status == (
        BusinessLearningCandidateStatus.REJECTED
    )
    assert rejected.approval_status == (
        BusinessLearningApprovalStatus.REJECTED
    )
    assert rejected.blocking_reasons == (
        "approval_rejected",
    )


def test_blocked_candidate_cannot_be_reviewed():
    factory = (
        BusinessLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=trusted_report(
            advisory_status=(
                BusinessLearningAdvisoryStatus.WATCH
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="pending validated",
    ):
        factory.review(
            candidate=candidate,
            approved=True,
            reviewed_by_user_id=uuid4(),
            reason="Should fail.",
        )


def test_review_cannot_be_repeated():
    factory = (
        BusinessLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=trusted_report()
    )
    approved = factory.review(
        candidate=candidate,
        approved=True,
        reviewed_by_user_id=uuid4(),
        reason="Approved.",
    )

    with pytest.raises(
        ValueError,
        match="pending validated",
    ):
        factory.review(
            candidate=approved,
            approved=True,
            reviewed_by_user_id=uuid4(),
            reason="Repeated.",
        )


def test_blank_review_reason_is_rejected():
    factory = (
        BusinessLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=trusted_report()
    )

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        factory.review(
            candidate=candidate,
            approved=True,
            reviewed_by_user_id=uuid4(),
            reason="   ",
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
def test_invalid_policy_values_are_rejected(
    keyword,
    value,
):
    with pytest.raises(ValueError):
        BusinessLearningInsightPolicy(
            **{keyword: value}
        )
