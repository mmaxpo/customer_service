from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    CapabilityLearningInsightCandidateRevisionRecord,
)
from app.runtime.capabilities.execution.learning.insight_candidates import (
    CapabilityLearningInsightCandidate,
)


class CapabilityLearningInsightCandidateRepository:
    """
    Append-only persistence for learning insight candidate revisions.

    Every user-facing query is scoped by authenticated user_id. Existing
    revisions are never updated.
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
        candidate: CapabilityLearningInsightCandidate,
    ) -> (
        CapabilityLearningInsightCandidateRevisionRecord
    ):
        lock_key = (
            "capability-learning-candidate:"
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
                    CapabilityLearningInsightCandidateRevisionRecord
                    .version
                )
            ).where(
                CapabilityLearningInsightCandidateRevisionRecord
                .candidate_id
                == candidate.candidate_id,
                CapabilityLearningInsightCandidateRevisionRecord
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
            CapabilityLearningInsightCandidateRevisionRecord(
                candidate_id=candidate.candidate_id,
                version=candidate.candidate_version,
                user_id=user_id,
                tenant_id=candidate.scope.tenant_id,
                capability_id=(
                    candidate.scope.capability_id
                ),
                provider_id=(
                    candidate.scope.provider_id
                ),
                provider_ref=(
                    candidate.scope.provider_ref
                ),
                action=candidate.scope.action,
                kind=candidate.kind.value,
                status=candidate.status.value,
                approval_status=(
                    candidate.approval_status.value
                ),
                promotion_target=(
                    candidate.promotion_target.value
                ),
                validation_passed=(
                    candidate.validation_passed
                ),
                promotion_eligible=(
                    candidate.promotion_eligible
                ),
                evidence_fingerprint=(
                    candidate
                    .evidence
                    .evidence_fingerprint
                ),
                reviewed_by_user_id=(
                    candidate.reviewed_by_user_id
                ),
                proposed_at=candidate.proposed_at,
                validated_at=candidate.validated_at,
                reviewed_at=candidate.reviewed_at,
                promoted_at=candidate.promoted_at,
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
        CapabilityLearningInsightCandidateRevisionRecord
        | None
    ):
        result = await self.db.execute(
            select(
                CapabilityLearningInsightCandidateRevisionRecord
            )
            .where(
                CapabilityLearningInsightCandidateRevisionRecord
                .user_id
                == user_id,
                CapabilityLearningInsightCandidateRevisionRecord
                .evidence_fingerprint
                == evidence_fingerprint,
            )
            .order_by(
                CapabilityLearningInsightCandidateRevisionRecord
                .created_at
                .desc(),
                CapabilityLearningInsightCandidateRevisionRecord
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
        CapabilityLearningInsightCandidateRevisionRecord
        | None
    ):
        result = await self.db.execute(
            select(
                CapabilityLearningInsightCandidateRevisionRecord
            )
            .where(
                CapabilityLearningInsightCandidateRevisionRecord
                .user_id
                == user_id,
                CapabilityLearningInsightCandidateRevisionRecord
                .candidate_id
                == candidate_id,
            )
            .order_by(
                CapabilityLearningInsightCandidateRevisionRecord
                .version
                .desc()
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def get_revision_for_user(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
        version: int,
    ) -> (
        CapabilityLearningInsightCandidateRevisionRecord
        | None
    ):
        result = await self.db.execute(
            select(
                CapabilityLearningInsightCandidateRevisionRecord
            ).where(
                CapabilityLearningInsightCandidateRevisionRecord
                .user_id
                == user_id,
                CapabilityLearningInsightCandidateRevisionRecord
                .candidate_id
                == candidate_id,
                CapabilityLearningInsightCandidateRevisionRecord
                .version
                == version,
            )
        )

        return result.scalar_one_or_none()

    async def list_history_for_user(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
    ) -> list[
        CapabilityLearningInsightCandidateRevisionRecord
    ]:
        result = await self.db.execute(
            select(
                CapabilityLearningInsightCandidateRevisionRecord
            )
            .where(
                CapabilityLearningInsightCandidateRevisionRecord
                .user_id
                == user_id,
                CapabilityLearningInsightCandidateRevisionRecord
                .candidate_id
                == candidate_id,
            )
            .order_by(
                CapabilityLearningInsightCandidateRevisionRecord
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
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        action: str | None = None,
        status: str | None = None,
        approval_status: str | None = None,
        promotion_eligible: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[
        CapabilityLearningInsightCandidateRevisionRecord
    ]:
        if limit < 1 or limit > 500:
            raise ValueError(
                "limit must be between 1 and 500"
            )

        if offset < 0:
            raise ValueError(
                "offset must be >= 0"
            )

        latest_version = (
            select(
                CapabilityLearningInsightCandidateRevisionRecord
                .candidate_id
                .label("candidate_id"),
                func.max(
                    CapabilityLearningInsightCandidateRevisionRecord
                    .version
                ).label("version"),
            )
            .where(
                CapabilityLearningInsightCandidateRevisionRecord
                .user_id
                == user_id
            )
            .group_by(
                CapabilityLearningInsightCandidateRevisionRecord
                .candidate_id
            )
            .subquery()
        )

        row = (
            CapabilityLearningInsightCandidateRevisionRecord
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
            (row.capability_id, capability_id),
            (row.provider_id, provider_id),
            (row.provider_ref, provider_ref),
            (row.action, action),
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

        if promotion_eligible is not None:
            stmt = stmt.where(
                row.promotion_eligible
                == bool(promotion_eligible)
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def deserialize(
        row: (
            CapabilityLearningInsightCandidateRevisionRecord
        ),
    ) -> CapabilityLearningInsightCandidate:
        return (
            CapabilityLearningInsightCandidate
            .model_validate(row.candidate_json)
        )


__all__ = [
    "CapabilityLearningInsightCandidateRepository",
]
