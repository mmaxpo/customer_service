from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import (
    func,
    or_,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    CapabilityRuntimePolicyRevisionRecord,
)
from app.runtime.capabilities.execution.policy.models import (
    CapabilityRuntimePolicyPatch,
    CapabilityRuntimePolicyRevision,
    CapabilityRuntimePolicyScope,
    CapabilityRuntimePolicySnapshot,
    merge_policy_revisions,
)


def normalize_policy_user_id(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value

    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(
            "user_id must be a valid UUID"
        ) from exc


class CapabilityRuntimePolicyRepository:
    """
    Append-only persistence and scoped policy queries.
    """

    POLICY_KEY = "capability_runtime"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def append_revision(
        self,
        *,
        scope: CapabilityRuntimePolicyScope,
        policy_payload: CapabilityRuntimePolicyPatch,
        enabled: bool = True,
        reason: str | None = None,
        created_by_user_id: UUID | str | None = None,
    ) -> CapabilityRuntimePolicyRevisionRecord:
        scope_key = scope.scope_key()

        # Serialize competing writers for the same logical scope.
        await self.db.execute(
            text(
                "SELECT pg_advisory_xact_lock("
                "hashtext(:scope_key)"
                ")"
            ),
            {"scope_key": scope_key},
        )

        current_version = await self.db.scalar(
            select(
                func.max(
                    CapabilityRuntimePolicyRevisionRecord
                    .version
                )
            ).where(
                CapabilityRuntimePolicyRevisionRecord
                .scope_key
                == scope_key
            )
        )

        record = CapabilityRuntimePolicyRevisionRecord(
            policy_key=self.POLICY_KEY,
            scope_key=scope_key,
            user_id=scope.user_id,
            tenant_id=scope.tenant_id,
            capability_id=scope.capability_id,
            provider_id=scope.provider_id,
            provider_ref=scope.provider_ref,
            version=int(current_version or 0) + 1,
            enabled=bool(enabled),
            policy_payload=(
                policy_payload.model_dump(
                    exclude_none=True,
                    mode="json",
                )
            ),
            reason=reason,
            created_by_user_id=(
                normalize_policy_user_id(
                    created_by_user_id
                )
                if created_by_user_id is not None
                else None
            ),
        )

        self.db.add(record)
        await self.db.flush()
        return record

    async def list_revisions(
        self,
        *,
        user_id: UUID | str,
        tenant_id: str | None = None,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CapabilityRuntimePolicyRevisionRecord]:
        normalized_user_id = normalize_policy_user_id(
            user_id
        )

        stmt = (
            select(
                CapabilityRuntimePolicyRevisionRecord
            )
            .where(
                CapabilityRuntimePolicyRevisionRecord
                .policy_key
                == self.POLICY_KEY,
                CapabilityRuntimePolicyRevisionRecord
                .user_id
                == normalized_user_id,
            )
            .order_by(
                CapabilityRuntimePolicyRevisionRecord
                .created_at
                .desc(),
                CapabilityRuntimePolicyRevisionRecord
                .version
                .desc(),
                CapabilityRuntimePolicyRevisionRecord
                .id
                .desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        if tenant_id is not None:
            stmt = stmt.where(
                CapabilityRuntimePolicyRevisionRecord
                .tenant_id
                == tenant_id
            )

        if capability_id is not None:
            stmt = stmt.where(
                CapabilityRuntimePolicyRevisionRecord
                .capability_id
                == capability_id
            )

        if provider_id is not None:
            stmt = stmt.where(
                CapabilityRuntimePolicyRevisionRecord
                .provider_id
                == provider_id
            )

        if provider_ref is not None:
            stmt = stmt.where(
                CapabilityRuntimePolicyRevisionRecord
                .provider_ref
                == provider_ref
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_matching_latest_revisions(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None,
        capability_id: str | None,
        provider_id: str | None,
        provider_ref: str | None,
    ) -> list[CapabilityRuntimePolicyRevisionRecord]:
        tenant_filter = (
            CapabilityRuntimePolicyRevisionRecord
            .tenant_id
            .is_(None)
        )

        if tenant_id is not None:
            tenant_filter = or_(
                CapabilityRuntimePolicyRevisionRecord
                .tenant_id
                .is_(None),
                CapabilityRuntimePolicyRevisionRecord
                .tenant_id
                == tenant_id,
            )

        capability_filter = (
            CapabilityRuntimePolicyRevisionRecord
            .capability_id
            .is_(None)
        )

        if capability_id is not None:
            capability_filter = or_(
                CapabilityRuntimePolicyRevisionRecord
                .capability_id
                .is_(None),
                CapabilityRuntimePolicyRevisionRecord
                .capability_id
                == capability_id,
            )

        provider_filter = (
            CapabilityRuntimePolicyRevisionRecord
            .provider_id
            .is_(None)
        )

        if provider_id is not None:
            provider_filter = or_(
                CapabilityRuntimePolicyRevisionRecord
                .provider_id
                .is_(None),
                CapabilityRuntimePolicyRevisionRecord
                .provider_id
                == provider_id,
            )

        provider_ref_filter = (
            CapabilityRuntimePolicyRevisionRecord
            .provider_ref
            .is_(None)
        )

        if provider_ref is not None:
            provider_ref_filter = or_(
                CapabilityRuntimePolicyRevisionRecord
                .provider_ref
                .is_(None),
                CapabilityRuntimePolicyRevisionRecord
                .provider_ref
                == provider_ref,
            )

        result = await self.db.execute(
            select(
                CapabilityRuntimePolicyRevisionRecord
            )
            .where(
                CapabilityRuntimePolicyRevisionRecord
                .policy_key
                == self.POLICY_KEY,
                CapabilityRuntimePolicyRevisionRecord
                .user_id
                == user_id,
                tenant_filter,
                capability_filter,
                provider_filter,
                provider_ref_filter,
            )
            .order_by(
                CapabilityRuntimePolicyRevisionRecord
                .scope_key
                .asc(),
                CapabilityRuntimePolicyRevisionRecord
                .version
                .desc(),
            )
        )

        records = list(result.scalars().all())

        # Select the highest version for every exact scope first.
        # Only after that do we apply enabled-state semantics.
        #
        # A disabled latest revision is a tombstone. It suppresses the scope
        # and must never reveal an older enabled revision.
        latest_by_scope = {}

        for record in records:
            existing = latest_by_scope.get(
                record.scope_key
            )

            if (
                existing is None
                or record.version > existing.version
            ):
                latest_by_scope[
                    record.scope_key
                ] = record

        return [
            record
            for record in latest_by_scope.values()
            if record.enabled
        ]


class DatabaseCapabilityRuntimePolicyReader:
    """
    Resolve field-level policy overrides using deterministic scope precedence.

    Missing or invalid authenticated ownership returns code defaults.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.repo = CapabilityRuntimePolicyRepository(db)

    async def resolve_policy(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str | None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
    ) -> CapabilityRuntimePolicySnapshot:
        try:
            normalized_user_id = (
                normalize_policy_user_id(user_id)
            )
        except ValueError:
            from app.runtime.capabilities.execution.policy.models import (
                NullCapabilityRuntimePolicyReader,
            )

            return await (
                NullCapabilityRuntimePolicyReader()
                .resolve_policy(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    capability_id=capability_id,
                    provider_id=provider_id,
                    provider_ref=provider_ref,
                )
            )

        records = (
            await self.repo.list_matching_latest_revisions(
                user_id=normalized_user_id,
                tenant_id=tenant_id,
                capability_id=capability_id,
                provider_id=provider_id,
                provider_ref=provider_ref,
            )
        )

        revisions = [
            self._revision(record)
            for record in records
        ]

        effective_policy = merge_policy_revisions(
            revisions=revisions,
            tenant_id=tenant_id,
        )

        ordered_revisions = tuple(
            sorted(
                revisions,
                key=lambda item: (
                    item.tenant_id is not None,
                    item.capability_id is not None,
                    item.provider_id is not None,
                    item.provider_ref is not None,
                    item.version,
                ),
            )
        )

        return CapabilityRuntimePolicySnapshot(
            found=bool(ordered_revisions),
            user_id=str(normalized_user_id),
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            effective_policy=effective_policy,
            applied_revisions=ordered_revisions,
            resolution_reason=(
                "durable_policy_merged"
                if ordered_revisions
                else "code_defaults"
            ),
        )

    @staticmethod
    def _revision(
        record: CapabilityRuntimePolicyRevisionRecord,
    ) -> CapabilityRuntimePolicyRevision:
        return CapabilityRuntimePolicyRevision(
            id=record.id,
            policy_key=record.policy_key,
            scope_key=record.scope_key,
            user_id=record.user_id,
            tenant_id=record.tenant_id,
            capability_id=record.capability_id,
            provider_id=record.provider_id,
            provider_ref=record.provider_ref,
            version=record.version,
            enabled=record.enabled,
            policy_payload=(
                CapabilityRuntimePolicyPatch
                .model_validate(
                    record.policy_payload or {}
                )
            ),
            reason=record.reason,
            created_by_user_id=(
                record.created_by_user_id
            ),
            created_at=record.created_at,
        )


__all__ = [
    "CapabilityRuntimePolicyRepository",
    "DatabaseCapabilityRuntimePolicyReader",
    "normalize_policy_user_id",
]
