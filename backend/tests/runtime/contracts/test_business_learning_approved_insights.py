from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.runtime.learning import (
    BusinessLearningApprovedInsight,
    BusinessLearningApprovedInsightProjection,
    BusinessLearningCandidateStatus,
    BusinessLearningInsightCandidateFactory,
)
from tests.runtime.contracts.test_business_learning_insight_candidates import (
    NOW,
    trusted_report,
)


def approved_candidate():
    factory = (
        BusinessLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=trusted_report(),
        proposed_at=NOW,
    )

    return factory.review(
        candidate=candidate,
        approved=True,
        reviewed_by_user_id=uuid4(),
        reason="Evidence accepted.",
        reviewed_at=NOW,
    )


def test_projects_approved_candidate():
    candidate = approved_candidate()

    insight = (
        BusinessLearningApprovedInsightProjection
        .from_candidate(candidate)
    )

    assert insight.scope.exact_key() == (
        "tenant-a",
        "customer_service.support",
        "multi_operation",
        "approved",
    )
    assert (
        insight.provenance.candidate_id
        == candidate.candidate_id
    )
    assert (
        insight.provenance.candidate_version
        == 2
    )
    assert (
        insight.provenance.evidence_fingerprint
        == candidate.evidence.evidence_fingerprint
    )

    assert insight.read_only is True
    assert insight.operator_review_only is True
    assert insight.affects_planning is False
    assert insight.affects_workflows is False
    assert insight.affects_routing is False
    assert insight.affects_runtime_policy is False
    assert (
        insight.authorizes_business_action
        is False
    )


def test_projection_uses_recent_evidence():
    candidate = approved_candidate()

    insight = (
        BusinessLearningApprovedInsightProjection
        .from_candidate(candidate)
    )

    recent = candidate.evidence.recent_summary
    trend = candidate.evidence.trend_report

    assert (
        insight.evidence.summary_confidence
        == recent.summary_confidence
    )
    assert (
        insight.evidence.estimated_success_rate
        == recent.estimated_success_rate
    )
    assert (
        insight.evidence.estimated_failure_rate
        == recent.estimated_failure_rate
    )
    assert (
        insight.evidence.contradiction_score
        == trend.contradiction_score
    )


def test_validated_candidate_cannot_be_projected():
    candidate = (
        BusinessLearningInsightCandidateFactory()
        .propose(
            report=trusted_report(),
            proposed_at=NOW,
        )
    )

    with pytest.raises(
        ValueError,
        match="Only approved candidates",
    ):
        (
            BusinessLearningApprovedInsightProjection
            .from_candidate(candidate)
        )


def test_rejected_candidate_cannot_be_projected():
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
        reason="Rejected.",
        reviewed_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match="Only approved candidates",
    ):
        (
            BusinessLearningApprovedInsightProjection
            .from_candidate(rejected)
        )


def test_scope_mismatch_is_rejected():
    candidate = approved_candidate()

    mismatched = candidate.model_copy(
        update={
            "scope": candidate.scope.model_copy(
                update={
                    "decision": "rejected"
                }
            )
        }
    )

    with pytest.raises(
        ValueError,
        match="scope does not match",
    ):
        (
            BusinessLearningApprovedInsightProjection
            .from_candidate(mismatched)
        )


@pytest.mark.parametrize(
    "field",
    [
        "affects_planning",
        "affects_workflows",
        "affects_routing",
        "affects_runtime_policy",
        "authorizes_business_action",
    ],
)
def test_safety_flags_cannot_be_enabled(
    field,
):
    insight = (
        BusinessLearningApprovedInsightProjection
        .from_candidate(
            approved_candidate()
        )
    )

    payload = insight.model_dump(
        mode="python"
    )
    payload[field] = True

    with pytest.raises(ValidationError):
        BusinessLearningApprovedInsight(
            **payload
        )


def test_projection_has_no_activation_fields():
    insight = (
        BusinessLearningApprovedInsightProjection
        .from_candidate(
            approved_candidate()
        )
    )

    payload = insight.model_dump(
        mode="json"
    )

    assert "promotion_id" not in payload
    assert "promotion_target" not in payload
    assert "active" not in payload
    assert "revoked" not in payload
    assert "recommended_behavior" not in payload
    assert "recommended_review" in payload
