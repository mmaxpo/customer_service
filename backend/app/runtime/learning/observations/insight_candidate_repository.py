from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    BusinessLearningInsightCandidateRevisionRecord,
)
from app.runtime.learning.observations.insight_candidates import (
    BusinessLearningInsightCandidate,
)


class BusinessLearningInsightCandidateRepository:
    """
    Append-only persistence for reviewable business
    insight candidate revisions.

    Every query is scoped by authenticated user_id.
    Existing revisions are never updated.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def append_revision(
        self,
        *,
        user_id: UUID,
        candidate: BusinessLearningInsightCandidate,
    ) -> (
        BusinessLearningInsightCandidateRevisionRecord
    ):
        lock_key = (
            "business-learning-candidate:"
            f"{candidate.candidate_id}"
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
                    BusinessLearningInsightCandidateRevisionRecord
                    .version
                )
            ).where(
                BusinessLearningInsightCandidateRevisionRecord
                .candidate_id
                == candidate.candidate_id,
                BusinessLearningInsightCandidateRevisionRecord
                .user_id
                == user_id,
            )
        )

        expected_version = (
            int(current_version or 0) + 1
        )

        if (
            candidate.candidate_version
            != expected_version
        ):
            raise ValueError(
                "candidate_version must be the "
                "next append-only revision"
            )

        row = (
            BusinessLearningInsightCandidateRevisionRecord(
                candidate_id=candidate.candidate_id,
                version=(
                    candidate.candidate_version
                ),
                user_id=user_id,
                tenant_id=(
                    candidate.scope.tenant_id
                ),
                objective_namespace=(
                    candidate.scope
                    .objective_namespace
                ),
                objective_type=(
                    candidate.scope.objective_type
                ),
                decision=(
                    candidate.scope.decision
                ),
                kind=candidate.kind.value,
                status=candidate.status.value,
                approval_status=(
                    candidate.approval_status.value
                ),
                validation_passed=(
                    candidate.validation_passed
                ),
                evidence_fingerprint=(
                    candidate.evidence
                    .evidence_fingerprint
                ),
                reviewed_by_user_id=(
                    candidate.reviewed_by_user_id
                ),
                proposed_at=candidate.proposed_at,
                validated_at=(
                    candidate.validated_at
                ),
                reviewed_at=candidate.reviewed_at,
                candidate_json=(
                    candidate.model_dump(
                        mode="json"
                    )
                ),
            )
        )

        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(row)

        return row

    async def get_latest_by_fingerprint_for_user(
        self,
        *,
        user_id: UUID,
        evidence_fingerprint: str,
    ) -> (
        BusinessLearningInsightCandidateRevisionRecord
        | None
    ):
        result = await self.db.execute(
            select(
                BusinessLearningInsightCandidateRevisionRecord
            )
            .where(
                BusinessLearningInsightCandidateRevisionRecord
                .user_id
                == user_id,
                BusinessLearningInsightCandidateRevisionRecord
                .evidence_fingerprint
                == evidence_fingerprint,
            )
            .order_by(
                BusinessLearningInsightCandidateRevisionRecord
                .created_at
                .desc(),
                BusinessLearningInsightCandidateRevisionRecord
                .version
                .desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def get_latest_for_user(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
    ) -> (
        BusinessLearningInsightCandidateRevisionRecord
        | None
    ):
        result = await self.db.execute(
            select(
                BusinessLearningInsightCandidateRevisionRecord
            )
            .where(
                BusinessLearningInsightCandidateRevisionRecord
                .user_id
                == user_id,
                BusinessLearningInsightCandidateRevisionRecord
                .candidate_id
                == candidate_id,
            )
            .order_by(
                BusinessLearningInsightCandidateRevisionRecord
                .version
                .desc()
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def list_history_for_user(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
    ) -> list[
        BusinessLearningInsightCandidateRevisionRecord
    ]:
        result = await self.db.execute(
            select(
                BusinessLearningInsightCandidateRevisionRecord
            )
            .where(
                BusinessLearningInsightCandidateRevisionRecord
                .user_id
                == user_id,
                BusinessLearningInsightCandidateRevisionRecord
                .candidate_id
                == candidate_id,
            )
            .order_by(
                BusinessLearningInsightCandidateRevisionRecord
                .version
                .asc()
            )
        )

        return list(result.scalars().all())

    async def list_latest_for_user(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
        objective_namespace: str | None = None,
        objective_type: str | None = None,
        decision: str | None = None,
        status: str | None = None,
        approval_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[
        BusinessLearningInsightCandidateRevisionRecord
    ]:
        if limit < 1 or limit > 500:
            raise ValueError(
                "limit must be between 1 and 500"
            )

        if offset < 0:
            raise ValueError(
                "offset must be >= 0"
            )

        row = (
            BusinessLearningInsightCandidateRevisionRecord
        )

        latest_version = (
            select(
                row.candidate_id.label(
                    "candidate_id"
                ),
                func.max(row.version).label(
                    "version"
                ),
            )
            .where(row.user_id == user_id)
            .group_by(row.candidate_id)
            .subquery()
        )

        stmt = (
            select(row)
            .join(
                latest_version,
                (
                    latest_version.c.candidate_id
                    == row.candidate_id
                )
                & (
                    latest_version.c.version
                    == row.version
                ),
            )
            .where(row.user_id == user_id)
            .order_by(
                row.created_at.desc(),
                row.candidate_id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        filters = (
            (row.tenant_id, tenant_id),
            (
                row.objective_namespace,
                objective_namespace,
            ),
            (
                row.objective_type,
                objective_type,
            ),
            (row.decision, decision),
            (row.status, status),
            (
                row.approval_status,
                approval_status,
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
        row: (
            BusinessLearningInsightCandidateRevisionRecord
        ),
    ) -> BusinessLearningInsightCandidate:
        return (
            BusinessLearningInsightCandidate
            .model_validate(row.candidate_json)
        )


__all__ = [
    "BusinessLearningInsightCandidateRepository",
]
