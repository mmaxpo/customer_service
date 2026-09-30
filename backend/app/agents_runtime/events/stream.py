from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator

from app.agents_runtime.events.types import AgentEvent


class AgentEventStream:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[AgentEvent]]] = defaultdict(
            list
        )

    async def publish(self, event: AgentEvent) -> None:
        subscribers = list(self._subscribers.get(event.agent_run_id, []))

        for queue in subscribers:
            await queue.put(event)

    async def subscribe(self, agent_run_id: str) -> AsyncIterator[AgentEvent]:
        queue: asyncio.Queue[AgentEvent] = asyncio.Queue()
        self._subscribers[agent_run_id].append(queue)

        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers[agent_run_id].remove(queue)

            if not self._subscribers[agent_run_id]:
                del self._subscribers[agent_run_id]

    def subscriber_count(self, agent_run_id: str) -> int:
        return len(self._subscribers.get(agent_run_id, []))
