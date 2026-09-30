from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.learning.insight_candidate_repository import (
    CapabilityLearningInsightCandidateRepository,
)
from app.runtime.capabilities.execution.learning.insight_promotion_repository import (
    CapabilityLearningInsightPromotionRepository,
)
from app.runtime.capabilities.execution.learning.insight_promotions import (
    CapabilityLearningPromotionStatus,
)
from app.runtime.capabilities.execution.learning.insight_candidates import (
    CapabilityLearningCandidateStatus,
    CapabilityLearningPromotionTarget,
)
from app.runtime.capabilities.execution.learning.planner_advisories import (
    CapabilityPlannerAdvisory,
    CapabilityPlannerAdvisoryProjection,
    CapabilityPlannerAdvisoryScope,
)


class CapabilityPlannerAdvisoryService:
    """
    Authenticated read-only projection of active planner promotions.

    It does not modify the capability planner, scores, registry, provider
    resolver, runtime policy, execution authorization, or verification.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        promotion_repository: (
            CapabilityLearningInsightPromotionRepository
            | None
        ) = None,
        candidate_repository: (
            CapabilityLearningInsightCandidateRepository
            | None
        ) = None,
    ) -> None:
        self.db = db
        self.promotion_repository = (
            promotion_repository
            or CapabilityLearningInsightPromotionRepository(
                db
            )
        )
        self.candidate_repository = (
            candidate_repository
            or CapabilityLearningInsightCandidateRepository(
                db
            )
        )

    async def list_for_scope(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str | None,
        provider_ref: str | None,
        action: str | None,
        limit: int = 100,
    ) -> list[CapabilityPlannerAdvisory]:
        if limit < 1 or limit > 500:
            raise ValueError(
                "limit must be between 1 and 500"
            )

        requested_scope = (
            CapabilityPlannerAdvisoryScope(
                tenant_id=tenant_id,
                capability_id=capability_id,
                provider_id=provider_id,
                provider_ref=provider_ref,
                action=action,
            )
        )

        rows = await (
            self.promotion_repository
            .list_latest_for_user(
                user_id=user_id,
                tenant_id=tenant_id,
                capability_id=capability_id,
                status=(
                    CapabilityLearningPromotionStatus
                    .ACTIVE
                    .value
                ),
                promotion_target=(
                    CapabilityLearningPromotionTarget
                    .PLANNER_ADVISORY
                    .value
                ),
                limit=limit,
                offset=0,
            )
        )

        advisories: list[
            CapabilityPlannerAdvisory
        ] = []

        for row in rows:
            promotion = (
                self.promotion_repository
                .deserialize(row)
            )

            promotion_scope = (
                CapabilityPlannerAdvisoryScope(
                    tenant_id=promotion.tenant_id,
                    capability_id=(
                        promotion.capability_id
                    ),
                    provider_id=(
                        promotion.provider_id
                    ),
                    provider_ref=(
                        promotion.provider_ref
                    ),
                    action=promotion.action,
                )
            )

            if (
                promotion_scope.exact_key()
                != requested_scope.exact_key()
            ):
                continue

            candidate_row = await (
                self.candidate_repository
                .get_revision_for_user(
                    user_id=user_id,
                    candidate_id=(
                        promotion.candidate_id
                    ),
                    version=(
                        promotion.candidate_version
                    ),
                )
            )

            if candidate_row is None:
                continue

            candidate = (
                self.candidate_repository
                .deserialize(candidate_row)
            )

            if (
                candidate.status
                != CapabilityLearningCandidateStatus
                .APPROVED
                or not candidate.promotion_eligible
                or candidate.blocking_reasons
            ):
                continue

            if (
                candidate.evidence
                .evidence_fingerprint
                != promotion.evidence_fingerprint
            ):
                continue

            advisories.append(
                CapabilityPlannerAdvisoryProjection
                .from_promotion(promotion)
            )

        return advisories


__all__ = [
    "CapabilityPlannerAdvisoryService",
]
