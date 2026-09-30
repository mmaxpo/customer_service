from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.capabilities.execution.learning import (
    CapabilityLearningAdvisoryStatus,
    CapabilityLearningCandidateGenerateRequest,
    CapabilityLearningCandidateReviewRequest,
    CapabilityLearningCandidateStatus,
    CapabilityLearningInsightCandidateOperations,
    CapabilityLearningInterpretation,
    CapabilityLearningQualityLevel,
    CapabilityLearningReviewDecision,
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


def summary(*, recent: bool):
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
        capability_id="capability.operations.test",
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


def report():
    historical = summary(recent=False)
    recent = summary(recent=True)

    return CapabilityLearningTrendReport(
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


class FakeTrendService:
    def __init__(self, reports):
        self.reports = list(reports)
        self.calls = []

    async def analyze(self, **kwargs):
        self.calls.append(kwargs)
        return list(self.reports)


class FakeRepository:
    def __init__(self):
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
                candidate.model_dump(mode="json")
            )
        )
        history.append(row)
        self.fingerprints[
            (
                user_id,
                candidate
                .evidence
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
    def deserialize(row):
        from app.runtime.capabilities.execution.learning import (
            CapabilityLearningInsightCandidate,
        )

        return (
            CapabilityLearningInsightCandidate
            .model_validate(row.candidate_json)
        )


@pytest.mark.asyncio
async def test_generate_persists_candidate_once():
    user_id = uuid4()
    repository = FakeRepository()
    trend_service = FakeTrendService(
        [report()]
    )
    operations = (
        CapabilityLearningInsightCandidateOperations(
            db=SimpleNamespace(),
            repository=repository,
            trend_service=trend_service,
        )
    )

    first = await operations.generate(
        user_id=user_id,
        request=(
            CapabilityLearningCandidateGenerateRequest()
        ),
    )
    second = await operations.generate(
        user_id=user_id,
        request=(
            CapabilityLearningCandidateGenerateRequest()
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
        CapabilityLearningInsightCandidateOperations(
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
            CapabilityLearningCandidateGenerateRequest()
        ),
    )
    candidate = generated.items[0].candidate

    reviewed = await operations.review(
        user_id=user_id,
        candidate_id=candidate.candidate_id,
        reviewed_by_user_id=user_id,
        request=(
            CapabilityLearningCandidateReviewRequest(
                decision=(
                    CapabilityLearningReviewDecision
                    .APPROVE
                ),
                reason="Evidence confirmed.",
            )
        ),
    )

    assert reviewed is not None
    assert reviewed.candidate_version == 2
    assert reviewed.status == (
        CapabilityLearningCandidateStatus
        .APPROVED
    )
    assert reviewed.promotion_eligible is True

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
        CapabilityLearningInsightCandidateOperations(
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
            CapabilityLearningCandidateGenerateRequest()
        ),
    )
    candidate_id = (
        generated.items[0].candidate.candidate_id
    )

    request = (
        CapabilityLearningCandidateReviewRequest(
            decision=(
                CapabilityLearningReviewDecision
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
        CapabilityLearningInsightCandidateOperations(
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
            CapabilityLearningCandidateGenerateRequest()
        ),
    )

    candidate_id = (
        generated.items[0].candidate.candidate_id
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
        CapabilityLearningInsightCandidateOperations(
            db=SimpleNamespace(),
            repository=FakeRepository(),
            trend_service=trend_service,
        )
    )

    await operations.generate(
        user_id=user_id,
        request=(
            CapabilityLearningCandidateGenerateRequest(
                tenant_id="tenant-a",
                capability_id="capability-a",
                provider_id="provider-a",
                provider_ref="provider-a.action",
                action="execute",
                window_hours=24,
            )
        ),
    )

    call = trend_service.calls[0]

    assert call["user_id"] == user_id
    assert call["tenant_id"] == "tenant-a"
    assert call["capability_id"] == (
        "capability-a"
    )
    assert call["provider_id"] == "provider-a"
    assert call["provider_ref"] == (
        "provider-a.action"
    )
    assert call["action"] == "execute"
    assert call["window_hours"] == 24
