from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.learning.insight_candidate_repository import (
    CapabilityLearningInsightCandidateRepository,
)
from app.runtime.capabilities.execution.learning.insight_promotion_repository import (
    CapabilityLearningInsightPromotionRepository,
)
from app.runtime.capabilities.execution.learning.insight_promotions import (
    CapabilityLearningInsightPromotion,
    CapabilityLearningPromotionFactory,
)


class CapabilityLearningPromotionCreateRequest(
    BaseModel
):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(
        min_length=1,
        max_length=4000,
    )


class CapabilityLearningPromotionRevokeRequest(
    BaseModel
):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(
        min_length=1,
        max_length=4000,
    )


class CapabilityLearningInsightPromotionOperations:
    """
    Explicit promotion and revocation operations.

    These operations only maintain an advisory promotion registry.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        candidate_repository: (
            CapabilityLearningInsightCandidateRepository
            | None
        ) = None,
        promotion_repository: (
            CapabilityLearningInsightPromotionRepository
            | None
        ) = None,
    ) -> None:
        self.db = db
        self.candidate_repository = (
            candidate_repository
            or CapabilityLearningInsightCandidateRepository(
                db
            )
        )
        self.promotion_repository = (
            promotion_repository
            or CapabilityLearningInsightPromotionRepository(
                db
            )
        )

    async def promote(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
        created_by_user_id: UUID,
        request: CapabilityLearningPromotionCreateRequest,
    ) -> CapabilityLearningInsightPromotion | None:
        candidate_row = await (
            self.candidate_repository
            .get_latest_for_user(
                user_id=user_id,
                candidate_id=candidate_id,
            )
        )

        if candidate_row is None:
            return None

        active = await (
            self.promotion_repository
            .get_active_for_candidate(
                user_id=user_id,
                candidate_id=candidate_id,
            )
        )

        if active is not None:
            raise ValueError(
                "Candidate already has an active "
                "promotion"
            )

        candidate = (
            self.candidate_repository.deserialize(
                candidate_row
            )
        )

        promotion = (
            CapabilityLearningPromotionFactory
            .promote(
                user_id=user_id,
                candidate=candidate,
                created_by_user_id=(
                    created_by_user_id
                ),
                reason=request.reason,
            )
        )

        row = await (
            self.promotion_repository.append_event(
                promotion=promotion
            )
        )

        return self.promotion_repository.deserialize(
            row
        )

    async def list_latest(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
        capability_id: str | None = None,
        candidate_id: UUID | None = None,
        status: str | None = None,
        promotion_target: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CapabilityLearningInsightPromotion]:
        rows = await (
            self.promotion_repository
            .list_latest_for_user(
                user_id=user_id,
                tenant_id=tenant_id,
                capability_id=capability_id,
                candidate_id=candidate_id,
                status=status,
                promotion_target=promotion_target,
                limit=limit,
                offset=offset,
            )
        )

        return [
            self.promotion_repository.deserialize(
                row
            )
            for row in rows
        ]

    async def get_latest(
        self,
        *,
        user_id: UUID,
        promotion_id: UUID,
    ) -> CapabilityLearningInsightPromotion | None:
        row = await (
            self.promotion_repository
            .get_latest_for_user(
                user_id=user_id,
                promotion_id=promotion_id,
            )
        )

        if row is None:
            return None

        return self.promotion_repository.deserialize(
            row
        )

    async def history(
        self,
        *,
        user_id: UUID,
        promotion_id: UUID,
    ) -> list[CapabilityLearningInsightPromotion]:
        rows = await (
            self.promotion_repository
            .list_history_for_user(
                user_id=user_id,
                promotion_id=promotion_id,
            )
        )

        return [
            self.promotion_repository.deserialize(
                row
            )
            for row in rows
        ]

    async def revoke(
        self,
        *,
        user_id: UUID,
        promotion_id: UUID,
        created_by_user_id: UUID,
        request: CapabilityLearningPromotionRevokeRequest,
    ) -> CapabilityLearningInsightPromotion | None:
        row = await (
            self.promotion_repository
            .get_latest_for_user(
                user_id=user_id,
                promotion_id=promotion_id,
            )
        )

        if row is None:
            return None

        current = (
            self.promotion_repository.deserialize(
                row
            )
        )

        revoked = (
            CapabilityLearningPromotionFactory
            .revoke(
                current=current,
                created_by_user_id=(
                    created_by_user_id
                ),
                reason=request.reason,
            )
        )

        appended = await (
            self.promotion_repository.append_event(
                promotion=revoked
            )
        )

        return self.promotion_repository.deserialize(
            appended
        )


__all__ = [
    "CapabilityLearningInsightPromotionOperations",
    "CapabilityLearningPromotionCreateRequest",
    "CapabilityLearningPromotionRevokeRequest",
]
