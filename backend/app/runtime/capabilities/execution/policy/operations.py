from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.policy.repository import (
    CapabilityRuntimePolicyRepository,
)


class CapabilityRuntimePolicyOperations:
    """
    Application-facing write operations for durable Runtime policy.

    Repositories own persistence mechanics inside a transaction.
    This operation owns transaction completion for the complete
    write use case.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: CapabilityRuntimePolicyRepository | None = None,
    ) -> None:
        self.db = db
        self.repository = (
            repository
            if repository is not None
            else CapabilityRuntimePolicyRepository(db)
        )

    async def append_revision(
        self,
        *,
        scope: Any,
        policy_payload: Any,
        enabled: bool,
        reason: str | None,
        created_by_user_id: Any,
    ) -> Any:
        try:
            row = await self.repository.append_revision(
                scope=scope,
                policy_payload=policy_payload,
                enabled=enabled,
                reason=reason,
                created_by_user_id=created_by_user_id,
            )

            await self.db.commit()
            await self.db.refresh(row)

            return row

        except ValueError:
            await self.db.rollback()
            raise


__all__ = [
    "CapabilityRuntimePolicyOperations",
]
