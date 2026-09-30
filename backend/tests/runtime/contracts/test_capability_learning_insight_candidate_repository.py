from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.capabilities.execution.learning import (
    CapabilityLearningAdvisoryStatus,
    CapabilityLearningInsightCandidateFactory,
    CapabilityLearningInsightCandidateRepository,
    CapabilityLearningInterpretation,
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
        capability_id="capability.repository.test",
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


def _report():
    historical = _summary(recent=False)
    recent = _summary(recent=True)

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


@pytest.mark.asyncio
async def test_repository_appends_and_reads_candidate_history():
    user_id = uuid4()
    reviewer_id = uuid4()
    factory = (
        CapabilityLearningInsightCandidateFactory()
    )

    candidate = factory.propose(
        report=_report(),
        proposed_at=NOW,
    )

    async with SessionLocal() as db:
        repository = (
            CapabilityLearningInsightCandidateRepository(
                db
            )
        )

        first = await repository.append_revision(
            user_id=user_id,
            candidate=candidate,
        )

        approved = factory.review(
            candidate=candidate,
            approved=True,
            reviewed_by_user_id=reviewer_id,
            reason="Confirmed.",
            reviewed_at=NOW,
        )

        second = await repository.append_revision(
            user_id=user_id,
            candidate=approved,
        )

        history = await (
            repository.list_history_for_user(
                user_id=user_id,
                candidate_id=candidate.candidate_id,
            )
        )

        latest = await (
            repository.get_latest_for_user(
                user_id=user_id,
                candidate_id=candidate.candidate_id,
            )
        )

        assert first.version == 1
        assert second.version == 2
        assert [
            row.version
            for row in history
        ] == [1, 2]
        assert latest is not None
        assert latest.status == "approved"
        assert latest.promotion_eligible is True

        restored = repository.deserialize(
            latest
        )

        assert restored == approved


@pytest.mark.asyncio
async def test_repository_rejects_version_gaps():
    user_id = uuid4()
    candidate = (
        CapabilityLearningInsightCandidateFactory()
        .propose(
            report=_report(),
            proposed_at=NOW,
        )
        .model_copy(
            update={"candidate_version": 2}
        )
    )

    async with SessionLocal() as db:
        repository = (
            CapabilityLearningInsightCandidateRepository(
                db
            )
        )

        with pytest.raises(
            ValueError,
            match="next append-only revision",
        ):
            await repository.append_revision(
                user_id=user_id,
                candidate=candidate,
            )

        await db.rollback()


@pytest.mark.asyncio
async def test_repository_enforces_cross_user_isolation():
    owner_id = uuid4()
    other_id = uuid4()
    candidate = (
        CapabilityLearningInsightCandidateFactory()
        .propose(
            report=_report(),
            proposed_at=NOW,
        )
    )

    async with SessionLocal() as db:
        repository = (
            CapabilityLearningInsightCandidateRepository(
                db
            )
        )

        await repository.append_revision(
            user_id=owner_id,
            candidate=candidate,
        )

        assert (
            await repository.get_latest_for_user(
                user_id=other_id,
                candidate_id=candidate.candidate_id,
            )
            is None
        )

        assert (
            await repository.list_history_for_user(
                user_id=other_id,
                candidate_id=candidate.candidate_id,
            )
            == []
        )


@pytest.mark.asyncio
async def test_list_latest_returns_only_latest_revision():
    user_id = uuid4()
    factory = (
        CapabilityLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=_report(),
        proposed_at=NOW,
    )

    async with SessionLocal() as db:
        repository = (
            CapabilityLearningInsightCandidateRepository(
                db
            )
        )

        await repository.append_revision(
            user_id=user_id,
            candidate=candidate,
        )

        approved = factory.review(
            candidate=candidate,
            approved=True,
            reviewed_by_user_id=uuid4(),
            reason="Confirmed.",
            reviewed_at=NOW,
        )

        await repository.append_revision(
            user_id=user_id,
            candidate=approved,
        )

        rows = await repository.list_latest_for_user(
            user_id=user_id,
            capability_id=(
                "capability.repository.test"
            ),
            promotion_eligible=True,
        )

        matching = [
            row
            for row in rows
            if row.candidate_id
            == candidate.candidate_id
        ]

        assert len(matching) == 1
        assert matching[0].version == 2


@pytest.mark.asyncio
async def test_duplicate_revision_is_rejected():
    user_id = uuid4()
    candidate = (
        CapabilityLearningInsightCandidateFactory()
        .propose(
            report=_report(),
            proposed_at=NOW,
        )
    )

    async with SessionLocal() as db:
        repository = (
            CapabilityLearningInsightCandidateRepository(
                db
            )
        )

        await repository.append_revision(
            user_id=user_id,
            candidate=candidate,
        )

        with pytest.raises(
            ValueError,
            match="next append-only revision",
        ):
            await repository.append_revision(
                user_id=user_id,
                candidate=candidate,
            )

        await db.rollback()
