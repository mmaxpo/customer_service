from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.agents_runtime.events import AgentEventType, InMemoryAgentEventStore
from app.agents_runtime.runner import AgentRunner
from app.agents_runtime.tools import build_builtin_tool_registry


@dataclass
class FakeMessage:
    content: str
    type: str = "message"


@dataclass
class FakeResponse:
    output: list
    output_text: str = ""


class FakeLLM:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls = 0

    async def respond(self, *, input_items: list, tools: list[dict]):
        response = self.responses[self.calls]
        self.calls += 1
        return response


@pytest.mark.asyncio
async def test_agent_runner_persists_events_to_event_store():
    event_store = InMemoryAgentEventStore()

    llm = FakeLLM(
        [
            FakeResponse(
                output=[FakeMessage(content="Hello")],
                output_text="Hello",
            )
        ]
    )

    runner = AgentRunner(
        llm=llm,
        tool_registry=build_builtin_tool_registry(),
        event_store=event_store,
    )

    state, recorder = await runner.run(user_input="Say hello")

    stored_events = await event_store.list_by_agent_run_id(state.agent_run_id)

    assert len(stored_events) == len(recorder.events)
    assert stored_events[0].type == AgentEventType.RUN_STARTED
    assert stored_events[-1].type == AgentEventType.RUN_COMPLETED
