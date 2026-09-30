from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ObjectiveLearningCandidateRevisionRecord,
)
from app.runtime.objectives.learning.lifecycle import (
    ObjectiveLearningCandidate,
)


class ObjectiveLearningCandidateRepository:
    """
    Append-only persistence for objective-learning candidate revisions.

    Every query is scoped by authenticated user_id. Existing revisions
    are never updated.
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
        candidate: ObjectiveLearningCandidate,
    ) -> ObjectiveLearningCandidateRevisionRecord:
        lock_key = f"objective-learning-candidate:{user_id}:{candidate.candidate_id}"

        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": lock_key},
        )

        current_version = await self.db.scalar(
            select(func.max(ObjectiveLearningCandidateRevisionRecord.version)).where(
                ObjectiveLearningCandidateRevisionRecord.candidate_id
                == candidate.candidate_id,
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
            )
        )

        expected_version = int(current_version or 0) + 1

        if candidate.candidate_version != expected_version:
            raise ValueError("candidate_version must be the next append-only revision")

        evidence = candidate.evidence

        row = ObjectiveLearningCandidateRevisionRecord(
            candidate_id=candidate.candidate_id,
            version=candidate.candidate_version,
            user_id=user_id,
            tenant_id=evidence.tenant_id,
            objective_namespace=(evidence.objective_namespace),
            objective_type=(evidence.objective_type),
            objective_version=(evidence.objective_version),
            schema_ref=evidence.schema_ref,
            profile_ref=evidence.profile_ref,
            profile_version=evidence.profile_version,
            extractor_ref=evidence.extractor_ref,
            extractor_version=(evidence.extractor_version),
            status=candidate.status.value,
            approval_status=(candidate.approval_status.value),
            validation_passed=(candidate.validation_passed),
            scope_fingerprint=(evidence.scope_fingerprint),
            policy_ref=candidate.policy_ref,
            policy_version=(candidate.policy_version),
            reviewed_by_user_id=(candidate.reviewed_by_user_id),
            proposed_at=candidate.proposed_at,
            validated_at=candidate.validated_at,
            reviewed_at=candidate.reviewed_at,
            candidate_json=candidate.model_dump(mode="json"),
            informational_only=(candidate.informational_only),
            authorizes_execution=(candidate.authorizes_execution),
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
        scope_fingerprint: str,
    ) -> ObjectiveLearningCandidateRevisionRecord | None:
        result = await self.db.execute(
            select(ObjectiveLearningCandidateRevisionRecord)
            .where(
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                ObjectiveLearningCandidateRevisionRecord.scope_fingerprint
                == scope_fingerprint,
            )
            .order_by(
                ObjectiveLearningCandidateRevisionRecord.created_at.desc(),
                ObjectiveLearningCandidateRevisionRecord.version.desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def get_latest_for_user(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
    ) -> ObjectiveLearningCandidateRevisionRecord | None:
        result = await self.db.execute(
            select(ObjectiveLearningCandidateRevisionRecord)
            .where(
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                ObjectiveLearningCandidateRevisionRecord.candidate_id == candidate_id,
            )
            .order_by(ObjectiveLearningCandidateRevisionRecord.version.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def get_revision_for_user(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
        version: int,
    ) -> ObjectiveLearningCandidateRevisionRecord | None:
        result = await self.db.execute(
            select(ObjectiveLearningCandidateRevisionRecord).where(
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                ObjectiveLearningCandidateRevisionRecord.candidate_id == candidate_id,
                ObjectiveLearningCandidateRevisionRecord.version == version,
            )
        )

        return result.scalar_one_or_none()

    async def list_history_for_user(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
    ) -> list[ObjectiveLearningCandidateRevisionRecord]:
        result = await self.db.execute(
            select(ObjectiveLearningCandidateRevisionRecord)
            .where(
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                ObjectiveLearningCandidateRevisionRecord.candidate_id == candidate_id,
            )
            .order_by(ObjectiveLearningCandidateRevisionRecord.version.asc())
        )

        return list(result.scalars().all())

    async def list_latest_for_user(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
        objective_namespace: str | None = None,
        objective_type: str | None = None,
        objective_version: int | None = None,
        schema_ref: str | None = None,
        profile_ref: str | None = None,
        profile_version: int | None = None,
        extractor_ref: str | None = None,
        extractor_version: int | None = None,
        status: str | None = None,
        approval_status: str | None = None,
        validation_passed: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ObjectiveLearningCandidateRevisionRecord]:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")

        if offset < 0:
            raise ValueError("offset must be >= 0")

        row = ObjectiveLearningCandidateRevisionRecord

        latest_version = (
            select(
                row.candidate_id.label("candidate_id"),
                func.max(row.version).label("version"),
            )
            .where(row.user_id == user_id)
            .group_by(row.candidate_id)
            .subquery()
        )

        stmt = (
            select(row)
            .join(
                latest_version,
                (latest_version.c.candidate_id == row.candidate_id)
                & (latest_version.c.version == row.version),
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
            (
                row.objective_version,
                objective_version,
            ),
            (row.schema_ref, schema_ref),
            (row.profile_ref, profile_ref),
            (
                row.profile_version,
                profile_version,
            ),
            (row.extractor_ref, extractor_ref),
            (
                row.extractor_version,
                extractor_version,
            ),
            (row.status, status),
            (
                row.approval_status,
                approval_status,
            ),
        )

        for column, value in filters:
            if value is not None:
                stmt = stmt.where(column == value)

        if validation_passed is not None:
            stmt = stmt.where(row.validation_passed == bool(validation_passed))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def deserialize(
        row: ObjectiveLearningCandidateRevisionRecord,
    ) -> ObjectiveLearningCandidate:
        return ObjectiveLearningCandidate.model_validate(row.candidate_json)


__all__ = [
    "ObjectiveLearningCandidateRepository",
]
