from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.learning import (
    BusinessLearningAdvisoryStatus,
    BusinessLearningCandidateGenerateRequest,
    BusinessLearningCandidateReviewRequest,
    BusinessLearningCandidateStatus,
    BusinessLearningEvidenceLevel,
    BusinessLearningInsightCandidate,
    BusinessLearningInsightCandidateOperations,
    BusinessLearningInterpretation,
    BusinessLearningReviewDecision,
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
        achieved=9,
        partially_achieved=0,
        progressing=0,
        failed=1,
        intentionally_not_executed=0,
        inconclusive=0,
        total_operations=10,
        achieved_operations=9,
        failed_operations=1,
        pending_operations=0,
        unknown_operations=0,
        not_executed_operations=0,
        average_confidence=0.95,
        evidence_coverage=1.0,
        finality_ratio=1.0,
        effective_sample_size=10.0,
        weighted_success_mass=9.0,
        weighted_failure_mass=1.0,
        weighted_unresolved_mass=0.0,
        weighted_not_executed_mass=0.0,
        estimated_success_rate=0.9,
        estimated_failure_rate=0.1,
        summary_confidence=0.95,
        minimum_effective_sample_size=5.0,
        evidence_sufficient=True,
        dominant_result="achieved",
        evidence_level=(
            BusinessLearningEvidenceLevel.HIGH
        ),
        interpretation=(
            BusinessLearningInterpretation.POSITIVE
        ),
    )


def report():
    historical = summary(recent=False)
    recent = summary(recent=True)

    return BusinessLearningTrendReport(
        tenant_id=historical.tenant_id,
        objective_namespace=(
            historical.objective_namespace
        ),
        objective_type=historical.objective_type,
        decision=historical.decision,
        historical=historical,
        recent=recent,
        historical_evidence_sufficient=True,
        recent_evidence_sufficient=True,
        comparison_evidence_sufficient=True,
        success_rate_delta=0.0,
        failure_rate_delta=0.0,
        confidence_delta=0.0,
        effective_sample_delta=0.0,
        result_distribution_divergence=0.0,
        contradiction_score=0.05,
        stability_score=0.95,
        interpretation_changed=False,
        dominant_result_changed=False,
        direct_interpretation_conflict=False,
        trend_direction=(
            BusinessLearningTrendDirection.STABLE
        ),
        stability_level=(
            BusinessLearningStabilityLevel.STABLE
        ),
        advisory_status=(
            BusinessLearningAdvisoryStatus.TRUST
        ),
        explanation="Stable business evidence.",
    )


class FakeTrendService:
    def __init__(
        self,
        reports,
    ):
        self.reports = list(reports)
        self.calls = []

    async def analyze(
        self,
        **kwargs,
    ):
        self.calls.append(kwargs)
        return list(self.reports)


class FakeRepository:
    def __init__(
        self,
    ):
        self.rows = {}
        self.fingerprints = {}

    async def get_latest_by_fingerprint_for_user(
        self,
        *,
        user_id,
        evidence_fingerprint,
    ):
        return self.fingerprints.get(
            (user_id, evidence_fingerprint)
        )

    async def append_revision(
        self,
        *,
        user_id,
        candidate,
    ):
        key = (
            user_id,
            candidate.candidate_id,
        )
        history = self.rows.setdefault(
            key,
            [],
        )

        row = SimpleNamespace(
            candidate_json=(
                candidate.model_dump(
                    mode="json"
                )
            )
        )

        history.append(row)

        self.fingerprints[
            (
                user_id,
                candidate.evidence
                .evidence_fingerprint,
            )
        ] = row

        return row

    async def get_latest_for_user(
        self,
        *,
        user_id,
        candidate_id,
    ):
        rows = self.rows.get(
            (user_id, candidate_id),
            [],
        )

        return rows[-1] if rows else None

    async def list_history_for_user(
        self,
        *,
        user_id,
        candidate_id,
    ):
        return list(
            self.rows.get(
                (user_id, candidate_id),
                [],
            )
        )

    async def list_latest_for_user(
        self,
        *,
        user_id,
        **kwargs,
    ):
        return [
            rows[-1]
            for (owner, _), rows
            in self.rows.items()
            if owner == user_id and rows
        ]

    @staticmethod
    def deserialize(
        row,
    ):
        return (
            BusinessLearningInsightCandidate
            .model_validate(
                row.candidate_json
            )
        )


@pytest.mark.asyncio
async def test_generate_persists_candidate_once():
    user_id = uuid4()
    repository = FakeRepository()
    trend_service = FakeTrendService(
        [report()]
    )

    operations = (
        BusinessLearningInsightCandidateOperations(
            db=SimpleNamespace(),
            repository=repository,
            trend_service=trend_service,
        )
    )

    first = await operations.generate(
        user_id=user_id,
        request=(
            BusinessLearningCandidateGenerateRequest()
        ),
    )
    second = await operations.generate(
        user_id=user_id,
        request=(
            BusinessLearningCandidateGenerateRequest()
        ),
    )

    assert first.created_candidates == 1
    assert first.existing_candidates == 0
    assert first.items[0].created is True

    assert second.created_candidates == 0
    assert second.existing_candidates == 1
    assert second.items[0].created is False

    assert (
        first.items[0].candidate.candidate_id
        == second.items[0].candidate.candidate_id
    )


@pytest.mark.asyncio
async def test_review_appends_approved_revision():
    user_id = uuid4()
    repository = FakeRepository()

    operations = (
        BusinessLearningInsightCandidateOperations(
            db=SimpleNamespace(),
            repository=repository,
            trend_service=FakeTrendService(
                [report()]
            ),
        )
    )

    generated = await operations.generate(
        user_id=user_id,
        request=(
            BusinessLearningCandidateGenerateRequest()
        ),
    )

    candidate = generated.items[0].candidate

    reviewed = await operations.review(
        user_id=user_id,
        candidate_id=candidate.candidate_id,
        reviewed_by_user_id=user_id,
        request=(
            BusinessLearningCandidateReviewRequest(
                decision=(
                    BusinessLearningReviewDecision
                    .APPROVE
                ),
                reason="Evidence confirmed.",
            )
        ),
    )

    assert reviewed is not None
    assert reviewed.candidate_version == 2
    assert reviewed.status == (
        BusinessLearningCandidateStatus.APPROVED
    )

    history = await operations.history(
        user_id=user_id,
        candidate_id=candidate.candidate_id,
    )

    assert [
        item.candidate_version
        for item in history
    ] == [1, 2]


@pytest.mark.asyncio
async def test_review_is_not_repeatable():
    user_id = uuid4()
    repository = FakeRepository()

    operations = (
        BusinessLearningInsightCandidateOperations(
            db=SimpleNamespace(),
            repository=repository,
            trend_service=FakeTrendService(
                [report()]
            ),
        )
    )

    generated = await operations.generate(
        user_id=user_id,
        request=(
            BusinessLearningCandidateGenerateRequest()
        ),
    )

    candidate_id = (
        generated.items[0]
        .candidate
        .candidate_id
    )

    request = (
        BusinessLearningCandidateReviewRequest(
            decision=(
                BusinessLearningReviewDecision
                .REJECT
            ),
            reason="Rejected.",
        )
    )

    await operations.review(
        user_id=user_id,
        candidate_id=candidate_id,
        reviewed_by_user_id=user_id,
        request=request,
    )

    with pytest.raises(
        ValueError,
        match="pending validated",
    ):
        await operations.review(
            user_id=user_id,
            candidate_id=candidate_id,
            reviewed_by_user_id=user_id,
            request=request,
        )


@pytest.mark.asyncio
async def test_cross_user_candidate_is_not_found():
    owner_id = uuid4()
    other_id = uuid4()
    repository = FakeRepository()

    operations = (
        BusinessLearningInsightCandidateOperations(
            db=SimpleNamespace(),
            repository=repository,
            trend_service=FakeTrendService(
                [report()]
            ),
        )
    )

    generated = await operations.generate(
        user_id=owner_id,
        request=(
            BusinessLearningCandidateGenerateRequest()
        ),
    )

    candidate_id = (
        generated.items[0]
        .candidate
        .candidate_id
    )

    assert (
        await operations.get_latest(
            user_id=other_id,
            candidate_id=candidate_id,
        )
        is None
    )


@pytest.mark.asyncio
async def test_generate_forwards_authenticated_scope():
    user_id = uuid4()
    trend_service = FakeTrendService([])

    operations = (
        BusinessLearningInsightCandidateOperations(
            db=SimpleNamespace(),
            repository=FakeRepository(),
            trend_service=trend_service,
        )
    )

    await operations.generate(
        user_id=user_id,
        request=(
            BusinessLearningCandidateGenerateRequest(
                tenant_id="tenant-a",
                objective_namespace=(
                    "customer_service.support"
                ),
                objective_type=(
                    "multi_operation"
                ),
                decision="approved",
                window_hours=24,
            )
        ),
    )

    call = trend_service.calls[0]

    assert call["user_id"] == user_id
    assert call["tenant_id"] == "tenant-a"
    assert (
        call["objective_namespace"]
        == "customer_service.support"
    )
    assert (
        call["objective_type"]
        == "multi_operation"
    )
    assert call["decision"] == "approved"
    assert call["window_hours"] == 24


@pytest.mark.asyncio
async def test_non_positive_or_negative_report_is_skipped():
    user_id = uuid4()
    mixed = report().model_copy(
        update={
            "recent": report().recent.model_copy(
                update={
                    "interpretation": (
                        BusinessLearningInterpretation
                        .MIXED
                    )
                }
            )
        }
    )

    operations = (
        BusinessLearningInsightCandidateOperations(
            db=SimpleNamespace(),
            repository=FakeRepository(),
            trend_service=FakeTrendService(
                [mixed]
            ),
        )
    )

    result = await operations.generate(
        user_id=user_id,
        request=(
            BusinessLearningCandidateGenerateRequest()
        ),
    )

    assert result.analyzed_reports == 1
    assert result.eligible_interpretations == 0
    assert result.created_candidates == 0
    assert result.items == ()
