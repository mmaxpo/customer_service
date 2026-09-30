from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ObjectiveLearningPolicyRevisionRecord,
)
from app.runtime.objectives.learning.contracts import (
    ObjectiveLearningProfile,
)
from app.runtime.objectives.learning.policy_revision import (
    ObjectiveLearningPolicyRevision,
    ObjectiveLearningPolicyScope,
)


class ObjectiveLearningPolicyRepository:
    """
    Append-only persistence for complete objective-learning policy
    snapshots.

    All reads are scoped to authenticated user ownership. Existing rows are
    never updated.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def ensure_revision(
        self,
        *,
        scope: ObjectiveLearningPolicyScope,
        profile: ObjectiveLearningProfile,
        enabled: bool = True,
        reason: str | None = None,
        created_by_user_id: UUID | None = None,
    ) -> tuple[ObjectiveLearningPolicyRevisionRecord, bool]:
        """
        Atomically create one exact immutable policy revision or return the
        identical revision that already exists.

        A persisted revision with the same semantic identity but different
        content is configuration drift and fails loudly. Existing durable
        history is never overwritten.
        """

        scope.validate_profile(profile)

        scope_key = scope.scope_key()
        policy_version = profile.qualification_policy.policy_version
        expected_profile_json = profile.model_dump(mode="json")

        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:scope_key))"),
            {"scope_key": scope_key},
        )

        existing = await self.get_revision_for_scope(
            scope=scope,
            policy_version=policy_version,
        )

        if existing is not None:
            mismatches: list[str] = []

            if existing.profile_version != profile.profile_version:
                mismatches.append("profile_version")

            if existing.profile_json != expected_profile_json:
                mismatches.append("profile_json")

            if existing.enabled is not bool(enabled):
                mismatches.append("enabled")

            if existing.informational_only is not True:
                mismatches.append("informational_only")

            if existing.authorizes_execution is not False:
                mismatches.append("authorizes_execution")

            if mismatches:
                raise ValueError(
                    "durable objective-learning policy revision "
                    "does not match the server-owned definition: "
                    + ", ".join(mismatches)
                )

            return existing, False

        created = await self.append_revision(
            scope=scope,
            profile=profile,
            enabled=enabled,
            reason=reason,
            created_by_user_id=created_by_user_id,
        )

        return created, True

    async def append_revision(
        self,
        *,
        scope: ObjectiveLearningPolicyScope,
        profile: ObjectiveLearningProfile,
        enabled: bool = True,
        reason: str | None = None,
        created_by_user_id: UUID | None = None,
    ) -> ObjectiveLearningPolicyRevisionRecord:
        scope.validate_profile(profile)

        scope_key = scope.scope_key()
        supplied_policy_version = profile.qualification_policy.policy_version

        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:scope_key))"),
            {"scope_key": scope_key},
        )

        current_version = await self.db.scalar(
            select(
                func.max(ObjectiveLearningPolicyRevisionRecord.policy_version)
            ).where(
                ObjectiveLearningPolicyRevisionRecord.scope_key == scope_key,
                ObjectiveLearningPolicyRevisionRecord.user_id == scope.user_id,
            )
        )

        expected_policy_version = int(current_version or 0) + 1

        if supplied_policy_version != expected_policy_version:
            raise ValueError(
                "objective-learning policy_version must be the next "
                "append-only revision"
            )

        record = ObjectiveLearningPolicyRevisionRecord(
            scope_key=scope_key,
            user_id=scope.user_id,
            tenant_id=scope.tenant_id,
            objective_namespace=scope.objective_namespace,
            objective_type=scope.objective_type,
            profile_ref=profile.profile_ref,
            profile_version=profile.profile_version,
            policy_ref=profile.qualification_policy.policy_ref,
            policy_version=supplied_policy_version,
            enabled=bool(enabled),
            profile_json=profile.model_dump(mode="json"),
            reason=reason,
            created_by_user_id=created_by_user_id,
            informational_only=True,
            authorizes_execution=False,
        )

        self.db.add(record)
        await self.db.flush()

        return record

    async def get_latest_for_scope(
        self,
        *,
        scope: ObjectiveLearningPolicyScope,
    ) -> ObjectiveLearningPolicyRevisionRecord | None:
        result = await self.db.execute(
            select(ObjectiveLearningPolicyRevisionRecord)
            .where(
                ObjectiveLearningPolicyRevisionRecord.user_id == scope.user_id,
                ObjectiveLearningPolicyRevisionRecord.scope_key == scope.scope_key(),
            )
            .order_by(
                ObjectiveLearningPolicyRevisionRecord.policy_version.desc(),
                ObjectiveLearningPolicyRevisionRecord.created_at.desc(),
                ObjectiveLearningPolicyRevisionRecord.id.desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def get_revision_for_scope(
        self,
        *,
        scope: ObjectiveLearningPolicyScope,
        policy_version: int,
    ) -> ObjectiveLearningPolicyRevisionRecord | None:
        result = await self.db.execute(
            select(ObjectiveLearningPolicyRevisionRecord).where(
                ObjectiveLearningPolicyRevisionRecord.user_id == scope.user_id,
                ObjectiveLearningPolicyRevisionRecord.scope_key == scope.scope_key(),
                ObjectiveLearningPolicyRevisionRecord.policy_version == policy_version,
            )
        )

        return result.scalar_one_or_none()

    async def list_revisions(
        self,
        *,
        scope: ObjectiveLearningPolicyScope,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ObjectiveLearningPolicyRevisionRecord]:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")

        if offset < 0:
            raise ValueError("offset must be >= 0")

        result = await self.db.execute(
            select(ObjectiveLearningPolicyRevisionRecord)
            .where(
                ObjectiveLearningPolicyRevisionRecord.user_id == scope.user_id,
                ObjectiveLearningPolicyRevisionRecord.scope_key == scope.scope_key(),
            )
            .order_by(
                ObjectiveLearningPolicyRevisionRecord.policy_version.desc(),
                ObjectiveLearningPolicyRevisionRecord.created_at.desc(),
                ObjectiveLearningPolicyRevisionRecord.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        return list(result.scalars().all())

    @staticmethod
    def deserialize(
        record: ObjectiveLearningPolicyRevisionRecord,
    ) -> ObjectiveLearningPolicyRevision:
        profile = ObjectiveLearningProfile.model_validate(record.profile_json)

        return ObjectiveLearningPolicyRevision(
            id=record.id,
            scope_key=record.scope_key,
            user_id=record.user_id,
            tenant_id=record.tenant_id,
            objective_namespace=record.objective_namespace,
            objective_type=record.objective_type,
            profile_ref=record.profile_ref,
            profile_version=record.profile_version,
            policy_ref=record.policy_ref,
            policy_version=record.policy_version,
            enabled=record.enabled,
            profile=profile,
            reason=record.reason,
            created_by_user_id=record.created_by_user_id,
            created_at=record.created_at,
            informational_only=record.informational_only,
            authorizes_execution=record.authorizes_execution,
        )


__all__ = [
    "ObjectiveLearningPolicyRepository",
]
