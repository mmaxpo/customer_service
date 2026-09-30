from __future__ import annotations

from app.agents_runtime.events.types import AgentEvent, AgentEventType


class EventRecorder:
    def __init__(self) -> None:
        self._events: list[AgentEvent] = []
        self._sequence = 0

    def emit(
        self,
        *,
        agent_run_id: str,
        event_type: AgentEventType,
        step: int,
        payload: dict | None = None,
    ) -> AgentEvent:
        self._sequence += 1

        event = AgentEvent(
            agent_run_id=agent_run_id,
            type=event_type,
            step=step,
            sequence=self._sequence,
            payload=payload or {},
        )

        self._events.append(event)
        return event

    @property
    def events(self) -> list[AgentEvent]:
        return list(self._events)

    def by_type(self, event_type: AgentEventType) -> list[AgentEvent]:
        return [event for event in self._events if event.type == event_type]

    def clear(self) -> None:
        self._events.clear()
        self._sequence = 0
