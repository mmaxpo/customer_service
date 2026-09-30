from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.capabilities.execution.learning import (
    CapabilityLearningInsightPromotionOperations,
    CapabilityLearningPromotionCreateRequest,
    CapabilityLearningPromotionRevokeRequest,
)


class FakeCandidateRepository:
    def __init__(self, candidate=None):
        self.candidate = candidate

    async def get_latest_for_user(
        self,
        *,
        user_id,
        candidate_id,
    ):
        if self.candidate is None:
            return None

        return SimpleNamespace(
            candidate_json=self.candidate
        )

    @staticmethod
    def deserialize(row):
        return row.candidate_json


class FakePromotionRepository:
    def __init__(self):
        self.rows = {}
        self.active_by_candidate = {}

    async def get_active_for_candidate(
        self,
        *,
        user_id,
        candidate_id,
    ):
        return self.active_by_candidate.get(
            (user_id, candidate_id)
        )

    async def append_event(
        self,
        *,
        promotion,
    ):
        key = (
            promotion.user_id,
            promotion.promotion_id,
        )
        self.rows.setdefault(key, []).append(
            SimpleNamespace(
                promotion_json=(
                    promotion.model_dump(
                        mode="json"
                    )
                )
            )
        )

        candidate_key = (
            promotion.user_id,
            promotion.candidate_id,
        )

        if promotion.status.value == "active":
            self.active_by_candidate[
                candidate_key
            ] = self.rows[key][-1]
        else:
            self.active_by_candidate.pop(
                candidate_key,
                None,
            )

        return self.rows[key][-1]

    async def get_latest_for_user(
        self,
        *,
        user_id,
        promotion_id,
    ):
        rows = self.rows.get(
            (user_id, promotion_id),
            [],
        )
        return rows[-1] if rows else None

    async def list_history_for_user(
        self,
        *,
        user_id,
        promotion_id,
    ):
        return list(
            self.rows.get(
                (user_id, promotion_id),
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
            CapabilityLearningInsightPromotion,
        )

        return (
            CapabilityLearningInsightPromotion
            .model_validate(
                row.promotion_json
            )
        )


@pytest.mark.asyncio
async def test_registry_list_get_and_history():
    repository = FakePromotionRepository()
    operations = (
        CapabilityLearningInsightPromotionOperations(
            db=SimpleNamespace(),
            candidate_repository=(
                FakeCandidateRepository()
            ),
            promotion_repository=repository,
        )
    )

    user_id = uuid4()
    promotion_id = uuid4()

    assert (
        await operations.get_latest(
            user_id=user_id,
            promotion_id=promotion_id,
        )
        is None
    )
    assert (
        await operations.history(
            user_id=user_id,
            promotion_id=promotion_id,
        )
        == []
    )
    assert (
        await operations.list_latest(
            user_id=user_id
        )
        == []
    )


@pytest.mark.asyncio
async def test_revoke_missing_promotion_returns_none():
    operations = (
        CapabilityLearningInsightPromotionOperations(
            db=SimpleNamespace(),
            candidate_repository=(
                FakeCandidateRepository()
            ),
            promotion_repository=(
                FakePromotionRepository()
            ),
        )
    )

    result = await operations.revoke(
        user_id=uuid4(),
        promotion_id=uuid4(),
        created_by_user_id=uuid4(),
        request=(
            CapabilityLearningPromotionRevokeRequest(
                reason="No record."
            )
        ),
    )

    assert result is None


@pytest.mark.asyncio
async def test_promote_missing_candidate_returns_none():
    operations = (
        CapabilityLearningInsightPromotionOperations(
            db=SimpleNamespace(),
            candidate_repository=(
                FakeCandidateRepository()
            ),
            promotion_repository=(
                FakePromotionRepository()
            ),
        )
    )

    result = await operations.promote(
        user_id=uuid4(),
        candidate_id=uuid4(),
        created_by_user_id=uuid4(),
        request=(
            CapabilityLearningPromotionCreateRequest(
                reason="Promote."
            )
        ),
    )

    assert result is None
