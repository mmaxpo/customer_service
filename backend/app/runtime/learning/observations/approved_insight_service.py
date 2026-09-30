from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.learning.observations.approved_insights import (
    BusinessLearningApprovedInsight,
    BusinessLearningApprovedInsightProjection,
)
from app.runtime.learning.observations.insight_candidate_repository import (
    BusinessLearningInsightCandidateRepository,
)
from app.runtime.learning.observations.insight_candidates import (
    BusinessLearningApprovalStatus,
    BusinessLearningCandidateStatus,
)


class BusinessLearningApprovedInsightService:
    """
    Authenticated read-only projection of approved
    business-learning candidates.

    This service performs no writes and does not
    activate or apply approved insights.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: (
            BusinessLearningInsightCandidateRepository
            | None
        ) = None,
    ) -> None:
        self.db = db
        self.repository = (
            repository
            or BusinessLearningInsightCandidateRepository(
                db
            )
        )

    async def list_approved(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
        objective_namespace: str | None = None,
        objective_type: str | None = None,
        decision: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BusinessLearningApprovedInsight]:
        rows = await (
            self.repository.list_latest_for_user(
                user_id=user_id,
                tenant_id=tenant_id,
                objective_namespace=(
                    objective_namespace
                ),
                objective_type=objective_type,
                decision=decision,
                status=(
                    BusinessLearningCandidateStatus
                    .APPROVED
                    .value
                ),
                approval_status=(
                    BusinessLearningApprovalStatus
                    .APPROVED
                    .value
                ),
                limit=limit,
                offset=offset,
            )
        )

        insights: list[
            BusinessLearningApprovedInsight
        ] = []

        for row in rows:
            candidate = (
                self.repository.deserialize(row)
            )

            insights.append(
                BusinessLearningApprovedInsightProjection
                .from_candidate(candidate)
            )

        return insights

    async def get_approved(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
    ) -> BusinessLearningApprovedInsight | None:
        row = await (
            self.repository.get_latest_for_user(
                user_id=user_id,
                candidate_id=candidate_id,
            )
        )

        if row is None:
            return None

        candidate = self.repository.deserialize(
            row
        )

        if (
            candidate.status
            != BusinessLearningCandidateStatus
            .APPROVED
            or candidate.approval_status
            != BusinessLearningApprovalStatus
            .APPROVED
        ):
            return None

        return (
            BusinessLearningApprovedInsightProjection
            .from_candidate(candidate)
        )


__all__ = [
    "BusinessLearningApprovedInsightService",
]
