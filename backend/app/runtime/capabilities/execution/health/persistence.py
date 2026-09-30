from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.health.decisions import (
    ProposedProviderHealthDecision,
)
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
)


class CapabilityProviderHealthPersistenceService:
    """
    Persist advisory scoped health state and append-only decision history.

    This service does not update ProviderHealthRegistry or resolver policy.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CapabilityProviderHealthRepository(
            db
        )

    async def persist(
        self,
        *,
        decision: ProposedProviderHealthDecision,
    ) -> dict:
        state, record, inserted = (
            await self.repo.persist_decision(
                decision=decision
            )
        )

        return {
            "inserted": inserted,
            "state_id": str(state.id),
            "decision_id": str(record.id),
            "scope_key": state.scope_key,
            "current_state": state.current_state,
            "state_version": state.version,
            "decision_key": record.decision_key,
            "evaluation_key": record.evaluation_key,
            "resulting_state": (
                record.resulting_state
            ),
        }


__all__ = [
    "CapabilityProviderHealthPersistenceService"
]
