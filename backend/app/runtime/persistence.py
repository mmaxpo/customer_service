"""
Public Runtime persistence boundary.

Consumers depend on generic Runtime persistence contracts. Runtime itself owns
selection and construction of the concrete persistence adapters.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.engine.persistence.postgres import (
    PostgresEventSink,
    PostgresRunStore,
)
from app.runtime.engine.persistence.types import (
    EventSink,
    RunStore,
)


def build_run_store(
    db: AsyncSession,
) -> RunStore:
    """
    Build the installed durable Runtime run store.

    Concrete persistence implementation ownership remains inside Runtime;
    application and product code consume only the RunStore contract.
    """

    return PostgresRunStore(db)


def build_event_sink(
    db: AsyncSession,
) -> EventSink:
    """
    Build the installed durable Runtime event sink.

    Concrete persistence implementation ownership remains inside Runtime;
    application and product code consume only the EventSink contract.
    """

    return PostgresEventSink(db)


__all__ = [
    "EventSink",
    "RunStore",
    "build_event_sink",
    "build_run_store",
]
