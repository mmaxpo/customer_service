from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.capabilities.execution.learning import (
    CapabilityLearningAdvisoryStatus,
    CapabilityLearningInsightCandidateFactory,
    CapabilityLearningInsightPromotionRepository,
    CapabilityLearningInterpretation,
    CapabilityLearningPromotionFactory,
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


def _approved_candidate():
    def summary(*, recent):
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
            capability_id="capability.promotion.repo",
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

    historical = summary(recent=False)
    recent = summary(recent=True)

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
    proposed = factory.propose(
        report=report,
        proposed_at=NOW,
    )

    return factory.review(
        candidate=proposed,
        approved=True,
        reviewed_by_user_id=uuid4(),
        reason="Confirmed.",
        reviewed_at=NOW,
    )


@pytest.mark.asyncio
async def test_repository_appends_promotion_and_revocation():
    user_id = uuid4()
    promoted = (
        CapabilityLearningPromotionFactory
        .promote(
            user_id=user_id,
            candidate=_approved_candidate(),
            created_by_user_id=user_id,
            reason="Promote.",
            created_at=NOW,
        )
    )

    async with SessionLocal() as db:
        repository = (
            CapabilityLearningInsightPromotionRepository(
                db
            )
        )

        first = await repository.append_event(
            promotion=promoted
        )

        revoked = (
            CapabilityLearningPromotionFactory
            .revoke(
                current=promoted,
                created_by_user_id=user_id,
                reason="Revoke.",
                created_at=NOW,
            )
        )

        second = await repository.append_event(
            promotion=revoked
        )

        history = await (
            repository.list_history_for_user(
                user_id=user_id,
                promotion_id=(
                    promoted.promotion_id
                ),
            )
        )

        latest = await (
            repository.get_latest_for_user(
                user_id=user_id,
                promotion_id=(
                    promoted.promotion_id
                ),
            )
        )

        assert first.event_version == 1
        assert second.event_version == 2
        assert [
            row.event_version
            for row in history
        ] == [1, 2]
        assert latest is not None
        assert latest.status == "revoked"


@pytest.mark.asyncio
async def test_repository_active_candidate_query():
    user_id = uuid4()
    candidate = _approved_candidate()
    promoted = (
        CapabilityLearningPromotionFactory
        .promote(
            user_id=user_id,
            candidate=candidate,
            created_by_user_id=user_id,
            reason="Promote.",
        )
    )

    async with SessionLocal() as db:
        repository = (
            CapabilityLearningInsightPromotionRepository(
                db
            )
        )

        await repository.append_event(
            promotion=promoted
        )

        active = await (
            repository.get_active_for_candidate(
                user_id=user_id,
                candidate_id=candidate.candidate_id,
            )
        )

        assert active is not None
        assert active.status == "active"

        revoked = (
            CapabilityLearningPromotionFactory
            .revoke(
                current=promoted,
                created_by_user_id=user_id,
                reason="Revoke.",
            )
        )
        await repository.append_event(
            promotion=revoked
        )

        assert (
            await repository.get_active_for_candidate(
                user_id=user_id,
                candidate_id=candidate.candidate_id,
            )
            is None
        )


@pytest.mark.asyncio
async def test_repository_enforces_user_isolation():
    owner_id = uuid4()
    other_id = uuid4()
    promoted = (
        CapabilityLearningPromotionFactory
        .promote(
            user_id=owner_id,
            candidate=_approved_candidate(),
            created_by_user_id=owner_id,
            reason="Promote.",
        )
    )

    async with SessionLocal() as db:
        repository = (
            CapabilityLearningInsightPromotionRepository(
                db
            )
        )

        await repository.append_event(
            promotion=promoted
        )

        assert (
            await repository.get_latest_for_user(
                user_id=other_id,
                promotion_id=(
                    promoted.promotion_id
                ),
            )
            is None
        )


@pytest.mark.asyncio
async def test_repository_rejects_version_gap():
    user_id = uuid4()
    promoted = (
        CapabilityLearningPromotionFactory
        .promote(
            user_id=user_id,
            candidate=_approved_candidate(),
            created_by_user_id=user_id,
            reason="Promote.",
        )
        .model_copy(
            update={"event_version": 2}
        )
    )

    async with SessionLocal() as db:
        repository = (
            CapabilityLearningInsightPromotionRepository(
                db
            )
        )

        with pytest.raises(
            ValueError,
            match="next append-only version",
        ):
            await repository.append_event(
                promotion=promoted
            )

        await db.rollback()
