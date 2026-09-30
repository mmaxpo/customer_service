from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.agents_runtime.state.schemas import AgentState
from app.agents_runtime.state.serialization import dump_agent_state, load_agent_state
from app.models.models import AgentRun


class AgentStateStore(Protocol):
    async def save(self, state: AgentState) -> None: ...

    async def load(self, agent_run_id: str) -> AgentState | None: ...

    async def delete(self, agent_run_id: str) -> None: ...


class InMemoryAgentStateStore:
    def __init__(self) -> None:
        self._states: dict[str, dict] = {}

    async def save(self, state: AgentState) -> None:
        self._states[state.agent_run_id] = dump_agent_state(state)

    async def load(self, agent_run_id: str) -> AgentState | None:
        data = self._states.get(agent_run_id)
        if data is None:
            return None
        return load_agent_state(data)

    async def delete(self, agent_run_id: str) -> None:
        self._states.pop(agent_run_id, None)

    async def clear(self) -> None:
        self._states.clear()


class PostgresAgentStateStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def save(self, state: AgentState) -> None:
        state_data = dump_agent_state(state)
        run_uuid = UUID(state.agent_run_id)

        stmt = insert(AgentRun).values(
            agent_run_id=run_uuid,
            status=str(
                state.status.value if hasattr(state.status, "value") else state.status
            ),
            state=state_data,
            usage=state.meta.get("usage"),
            extra=state.meta,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=[AgentRun.agent_run_id],
            set_={
                "status": str(
                    state.status.value
                    if hasattr(state.status, "value")
                    else state.status
                ),
                "state": state_data,
                "usage": state.meta.get("usage"),
                "extra": state.meta,
            },
        )

        async with self.session_factory() as session:
            await session.execute(stmt)
            await session.commit()

    async def load(self, agent_run_id: str) -> AgentState | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(AgentRun).where(AgentRun.agent_run_id == UUID(agent_run_id))
            )
            row = result.scalar_one_or_none()

            if row is None:
                return None

            return load_agent_state(row.state)

    async def delete(self, agent_run_id: str) -> None:
        async with self.session_factory() as session:
            row = await session.get(AgentRun, UUID(agent_run_id))
            if row is not None:
                await session.delete(row)
                await session.commit()
