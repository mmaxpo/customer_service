from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    CapabilityLearningInsightPromotionRecord,
)
from app.runtime.capabilities.execution.learning.insight_promotions import (
    CapabilityLearningInsightPromotion,
)


class CapabilityLearningInsightPromotionRepository:
    """
    Append-only promotion lifecycle repository.

    Every user-facing query is authenticated-user scoped. Existing promotion
    events are never updated.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def append_event(
        self,
        *,
        promotion: CapabilityLearningInsightPromotion,
    ) -> CapabilityLearningInsightPromotionRecord:
        lock_key = (
            "capability-learning-promotion:"
            f"{promotion.promotion_id}"
        )

        await self.db.execute(
            text(
                "SELECT pg_advisory_xact_lock("
                "hashtext(:lock_key)"
                ")"
            ),
            {"lock_key": lock_key},
        )

        current_version = await self.db.scalar(
            select(
                func.max(
                    CapabilityLearningInsightPromotionRecord
                    .event_version
                )
            ).where(
                CapabilityLearningInsightPromotionRecord
                .promotion_id
                == promotion.promotion_id,
                CapabilityLearningInsightPromotionRecord
                .user_id
                == promotion.user_id,
            )
        )

        expected_version = (
            int(current_version or 0) + 1
        )

        if (
            promotion.event_version
            != expected_version
        ):
            raise ValueError(
                "promotion event_version must be "
                "the next append-only version"
            )

        row = CapabilityLearningInsightPromotionRecord(
            promotion_id=promotion.promotion_id,
            event_version=promotion.event_version,
            candidate_id=promotion.candidate_id,
            candidate_version=(
                promotion.candidate_version
            ),
            user_id=promotion.user_id,
            tenant_id=promotion.tenant_id,
            capability_id=promotion.capability_id,
            provider_id=promotion.provider_id,
            provider_ref=promotion.provider_ref,
            action=promotion.action,
            event_type=promotion.event_type.value,
            status=promotion.status.value,
            promotion_target=(
                promotion.promotion_target.value
            ),
            evidence_fingerprint=(
                promotion.evidence_fingerprint
            ),
            reason=promotion.reason,
            created_by_user_id=(
                promotion.created_by_user_id
            ),
            promotion_json=(
                promotion.model_dump(mode="json")
            ),
            created_at=promotion.created_at,
        )

        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(row)

        return row

    async def get_latest_for_user(
        self,
        *,
        user_id: UUID,
        promotion_id: UUID,
    ) -> (
        CapabilityLearningInsightPromotionRecord
        | None
    ):
        result = await self.db.execute(
            select(
                CapabilityLearningInsightPromotionRecord
            )
            .where(
                CapabilityLearningInsightPromotionRecord
                .user_id
                == user_id,
                CapabilityLearningInsightPromotionRecord
                .promotion_id
                == promotion_id,
            )
            .order_by(
                CapabilityLearningInsightPromotionRecord
                .event_version
                .desc()
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def get_active_for_candidate(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
    ) -> (
        CapabilityLearningInsightPromotionRecord
        | None
    ):
        latest = (
            select(
                CapabilityLearningInsightPromotionRecord
                .promotion_id
                .label("promotion_id"),
                func.max(
                    CapabilityLearningInsightPromotionRecord
                    .event_version
                ).label("event_version"),
            )
            .where(
                CapabilityLearningInsightPromotionRecord
                .user_id
                == user_id,
                CapabilityLearningInsightPromotionRecord
                .candidate_id
                == candidate_id,
            )
            .group_by(
                CapabilityLearningInsightPromotionRecord
                .promotion_id
            )
            .subquery()
        )

        row = CapabilityLearningInsightPromotionRecord

        result = await self.db.execute(
            select(row)
            .join(
                latest,
                (
                    latest.c.promotion_id
                    == row.promotion_id
                )
                & (
                    latest.c.event_version
                    == row.event_version
                ),
            )
            .where(
                row.user_id == user_id,
                row.candidate_id == candidate_id,
                row.status == "active",
            )
            .order_by(
                row.created_at.desc()
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def list_history_for_user(
        self,
        *,
        user_id: UUID,
        promotion_id: UUID,
    ) -> list[
        CapabilityLearningInsightPromotionRecord
    ]:
        result = await self.db.execute(
            select(
                CapabilityLearningInsightPromotionRecord
            )
            .where(
                CapabilityLearningInsightPromotionRecord
                .user_id
                == user_id,
                CapabilityLearningInsightPromotionRecord
                .promotion_id
                == promotion_id,
            )
            .order_by(
                CapabilityLearningInsightPromotionRecord
                .event_version
                .asc()
            )
        )

        return list(result.scalars().all())

    async def list_latest_for_user(
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
    ) -> list[
        CapabilityLearningInsightPromotionRecord
    ]:
        if limit < 1 or limit > 500:
            raise ValueError(
                "limit must be between 1 and 500"
            )

        if offset < 0:
            raise ValueError(
                "offset must be >= 0"
            )

        latest = (
            select(
                CapabilityLearningInsightPromotionRecord
                .promotion_id
                .label("promotion_id"),
                func.max(
                    CapabilityLearningInsightPromotionRecord
                    .event_version
                ).label("event_version"),
            )
            .where(
                CapabilityLearningInsightPromotionRecord
                .user_id
                == user_id
            )
            .group_by(
                CapabilityLearningInsightPromotionRecord
                .promotion_id
            )
            .subquery()
        )

        row = CapabilityLearningInsightPromotionRecord

        stmt = (
            select(row)
            .join(
                latest,
                (
                    latest.c.promotion_id
                    == row.promotion_id
                )
                & (
                    latest.c.event_version
                    == row.event_version
                ),
            )
            .where(row.user_id == user_id)
            .order_by(
                row.created_at.desc(),
                row.promotion_id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        filters = (
            (row.tenant_id, tenant_id),
            (row.capability_id, capability_id),
            (row.candidate_id, candidate_id),
            (row.status, status),
            (
                row.promotion_target,
                promotion_target,
            ),
        )

        for column, value in filters:
            if value is not None:
                stmt = stmt.where(
                    column == value
                )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def deserialize(
        row: CapabilityLearningInsightPromotionRecord,
    ) -> CapabilityLearningInsightPromotion:
        return (
            CapabilityLearningInsightPromotion
            .model_validate(row.promotion_json)
        )


__all__ = [
    "CapabilityLearningInsightPromotionRepository",
]
