from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.learning import (
    BusinessLearningAdvisoryStatus,
    BusinessLearningEvidenceLevel,
    BusinessLearningInsightCandidateFactory,
    BusinessLearningInsightCandidateRepository,
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
        objective_type=(
            historical.objective_type
        ),
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


@pytest.mark.asyncio
async def test_repository_appends_and_reads_history():
    user_id = uuid4()
    reviewer_id = uuid4()
    factory = (
        BusinessLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=report(),
        proposed_at=NOW,
    )

    async with SessionLocal() as db:
        repository = (
            BusinessLearningInsightCandidateRepository(
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
                candidate_id=(
                    candidate.candidate_id
                ),
            )
        )
        latest = await (
            repository.get_latest_for_user(
                user_id=user_id,
                candidate_id=(
                    candidate.candidate_id
                ),
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
        assert not hasattr(
            latest,
            "promotion_eligible",
        )

        restored = repository.deserialize(
            latest
        )
        assert restored == approved


@pytest.mark.asyncio
async def test_repository_rejects_version_gap():
    user_id = uuid4()
    candidate = (
        BusinessLearningInsightCandidateFactory()
        .propose(
            report=report(),
            proposed_at=NOW,
        )
        .model_copy(
            update={"candidate_version": 2}
        )
    )

    async with SessionLocal() as db:
        repository = (
            BusinessLearningInsightCandidateRepository(
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
async def test_repository_enforces_user_isolation():
    owner_id = uuid4()
    other_id = uuid4()
    candidate = (
        BusinessLearningInsightCandidateFactory()
        .propose(
            report=report(),
            proposed_at=NOW,
        )
    )

    async with SessionLocal() as db:
        repository = (
            BusinessLearningInsightCandidateRepository(
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
                candidate_id=(
                    candidate.candidate_id
                ),
            )
            is None
        )

        assert (
            await repository.list_history_for_user(
                user_id=other_id,
                candidate_id=(
                    candidate.candidate_id
                ),
            )
            == []
        )


@pytest.mark.asyncio
async def test_list_latest_returns_latest_revision():
    user_id = uuid4()
    factory = (
        BusinessLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=report(),
        proposed_at=NOW,
    )

    async with SessionLocal() as db:
        repository = (
            BusinessLearningInsightCandidateRepository(
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
            objective_namespace=(
                "customer_service.support"
            ),
            status="approved",
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
        BusinessLearningInsightCandidateFactory()
        .propose(
            report=report(),
            proposed_at=NOW,
        )
    )

    async with SessionLocal() as db:
        repository = (
            BusinessLearningInsightCandidateRepository(
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
