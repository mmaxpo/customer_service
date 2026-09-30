from __future__ import annotations

from collections import defaultdict
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents_runtime.events.types import AgentEvent
from app.models.models import AgentRunEvent


class AgentEventStore(Protocol):
    async def append(self, event: AgentEvent) -> None: ...

    async def append_many(self, events: list[AgentEvent]) -> None: ...

    async def list_by_agent_run_id(self, agent_run_id: str) -> list[AgentEvent]: ...


class InMemoryAgentEventStore:
    def __init__(self) -> None:
        self._events_by_agent_run_id: dict[str, list[AgentEvent]] = defaultdict(list)

    async def append(self, event: AgentEvent) -> None:
        self._events_by_agent_run_id[event.agent_run_id].append(event)

    async def append_many(self, events: list[AgentEvent]) -> None:
        for event in events:
            await self.append(event)

    async def list_by_agent_run_id(self, agent_run_id: str) -> list[AgentEvent]:
        return list(self._events_by_agent_run_id.get(agent_run_id, []))

    async def clear(self) -> None:
        self._events_by_agent_run_id.clear()


class PostgresAgentEventStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def append(self, event: AgentEvent) -> None:
        await self.append_many([event])

    async def append_many(self, events: list[AgentEvent]) -> None:
        if not events:
            return

        agent_run_id = events[0].agent_run_id
        run_uuid = UUID(agent_run_id)

        async with self.session_factory() as session:
            result = await session.execute(
                select(func.coalesce(func.max(AgentRunEvent.sequence), 0)).where(
                    AgentRunEvent.agent_run_id == run_uuid
                )
            )
            current_max_sequence = int(result.scalar_one())

            rows = []

            for index, event in enumerate(events, start=1):
                sequence = current_max_sequence + index
                event_data = event.model_dump(mode="json")
                event_data["sequence"] = sequence
                event_data["agent_run_id"] = agent_run_id
                event_data.pop("run_id", None)

                rows.append(
                    AgentRunEvent(
                        agent_run_id=run_uuid,
                        sequence=sequence,
                        event=event_data,
                    )
                )

            session.add_all(rows)
            await session.commit()

    async def list_by_agent_run_id(self, agent_run_id: str) -> list[AgentEvent]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(AgentRunEvent)
                .where(AgentRunEvent.agent_run_id == UUID(agent_run_id))
                .order_by(AgentRunEvent.sequence.asc(), AgentRunEvent.id.asc())
            )

            rows = result.scalars().all()

            return [AgentEvent.model_validate(row.event) for row in rows]

    # Backward-compatible alias while refactor finishes.
    async def list_by_run_id(self, agent_run_id: str) -> list[AgentEvent]:
        return await self.list_by_agent_run_id(agent_run_id)
