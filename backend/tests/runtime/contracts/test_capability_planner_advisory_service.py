from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.capabilities.execution.learning import (
    CapabilityLearningCandidateStatus,
    CapabilityLearningInsightPromotion,
    CapabilityLearningPromotionEventType,
    CapabilityLearningPromotionStatus,
    CapabilityLearningPromotionTarget,
    CapabilityPlannerAdvisoryService,
)


NOW = datetime(
    2026,
    7,
    19,
    12,
    0,
    tzinfo=timezone.utc,
)


def _promotion(
    *,
    user_id,
    provider_id="shopify",
):
    candidate_id = uuid4()

    promotion = CapabilityLearningInsightPromotion(
        promotion_id=uuid4(),
        event_version=1,
        candidate_id=candidate_id,
        candidate_version=2,
        user_id=user_id,
        tenant_id="tenant-a",
        capability_id="ecommerce.orders.get",
        provider_id=provider_id,
        provider_ref="shopify.orders.get",
        action="read",
        event_type=(
            CapabilityLearningPromotionEventType
            .PROMOTED
        ),
        status=(
            CapabilityLearningPromotionStatus
            .ACTIVE
        ),
        promotion_target=(
            CapabilityLearningPromotionTarget
            .PLANNER_ADVISORY
        ),
        evidence_fingerprint="a" * 64,
        reason="Approved.",
        created_by_user_id=user_id,
        created_at=NOW,
        promotion_payload={
            "candidate": {
                "kind": (
                    "positive_outcome_pattern"
                ),
                "scope": {
                    "tenant_id": "tenant-a",
                    "capability_id": (
                        "ecommerce.orders.get"
                    ),
                    "provider_id": provider_id,
                    "provider_ref": (
                        "shopify.orders.get"
                    ),
                    "action": "read",
                },
                "statement": "Stable outcome.",
                "recommended_behavior": (
                    "Surface as context."
                ),
                "limitations": [],
            }
        },
    )

    candidate = SimpleNamespace(
        status=(
            CapabilityLearningCandidateStatus
            .APPROVED
        ),
        promotion_eligible=True,
        blocking_reasons=(),
        evidence=SimpleNamespace(
            evidence_fingerprint="a" * 64
        ),
    )

    return promotion, candidate


class FakePromotionRepository:
    def __init__(self, promotions):
        self.promotions = promotions
        self.captured = None

    async def list_latest_for_user(
        self,
        **kwargs,
    ):
        self.captured = kwargs
        return [
            SimpleNamespace(
                promotion=promotion
            )
            for promotion in self.promotions
            if promotion.user_id
            == kwargs["user_id"]
        ]

    @staticmethod
    def deserialize(row):
        return row.promotion


class FakeCandidateRepository:
    def __init__(self, candidates):
        self.candidates = candidates
        self.captured = []

    async def get_revision_for_user(
        self,
        **kwargs,
    ):
        self.captured.append(kwargs)
        candidate = self.candidates.get(
            (
                kwargs["user_id"],
                kwargs["candidate_id"],
                kwargs["version"],
            )
        )

        if candidate is None:
            return None

        return SimpleNamespace(
            candidate=candidate
        )

    @staticmethod
    def deserialize(row):
        return row.candidate


@pytest.mark.asyncio
async def test_service_returns_exact_scope_only():
    user_id = uuid4()

    matching, candidate = _promotion(
        user_id=user_id,
    )
    wrong_provider, wrong_candidate = (
        _promotion(
            user_id=user_id,
            provider_id="other-provider",
        )
    )

    promotion_repository = (
        FakePromotionRepository(
            [matching, wrong_provider]
        )
    )
    candidate_repository = (
        FakeCandidateRepository(
            {
                (
                    user_id,
                    matching.candidate_id,
                    2,
                ): candidate,
                (
                    user_id,
                    wrong_provider.candidate_id,
                    2,
                ): wrong_candidate,
            }
        )
    )

    service = CapabilityPlannerAdvisoryService(
        db=SimpleNamespace(),
        promotion_repository=(
            promotion_repository
        ),
        candidate_repository=(
            candidate_repository
        ),
    )

    advisories = await service.list_for_scope(
        user_id=user_id,
        tenant_id="tenant-a",
        capability_id="ecommerce.orders.get",
        provider_id="shopify",
        provider_ref="shopify.orders.get",
        action="read",
    )

    assert len(advisories) == 1
    assert (
        advisories[0]
        .provenance
        .promotion_id
        == matching.promotion_id
    )

    assert promotion_repository.captured[
        "user_id"
    ] == user_id
    assert promotion_repository.captured[
        "status"
    ] == "active"
    assert promotion_repository.captured[
        "promotion_target"
    ] == "planner_advisory"


@pytest.mark.asyncio
async def test_service_excludes_missing_candidate():
    user_id = uuid4()
    promotion, _ = _promotion(
        user_id=user_id
    )

    service = CapabilityPlannerAdvisoryService(
        db=SimpleNamespace(),
        promotion_repository=(
            FakePromotionRepository(
                [promotion]
            )
        ),
        candidate_repository=(
            FakeCandidateRepository({})
        ),
    )

    advisories = await service.list_for_scope(
        user_id=user_id,
        tenant_id="tenant-a",
        capability_id="ecommerce.orders.get",
        provider_id="shopify",
        provider_ref="shopify.orders.get",
        action="read",
    )

    assert advisories == []


@pytest.mark.asyncio
async def test_service_excludes_other_user():
    owner_id = uuid4()
    other_id = uuid4()
    promotion, candidate = _promotion(
        user_id=owner_id
    )

    service = CapabilityPlannerAdvisoryService(
        db=SimpleNamespace(),
        promotion_repository=(
            FakePromotionRepository(
                [promotion]
            )
        ),
        candidate_repository=(
            FakeCandidateRepository(
                {
                    (
                        owner_id,
                        promotion.candidate_id,
                        2,
                    ): candidate,
                }
            )
        ),
    )

    advisories = await service.list_for_scope(
        user_id=other_id,
        tenant_id="tenant-a",
        capability_id="ecommerce.orders.get",
        provider_id="shopify",
        provider_ref="shopify.orders.get",
        action="read",
    )

    assert advisories == []
