from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.agents_runtime.events import AgentEventStream, AgentEventType
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
async def test_agent_runner_publishes_events_to_stream():
    stream = AgentEventStream()

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
        event_stream=stream,
    )

    state, recorder = await runner.run(user_input="Say hello")

    # No subscribers here, so this only verifies publishing path does not fail.
    assert state.final_output == "Hello"
    assert recorder.events[0].type == AgentEventType.RUN_STARTED
    assert recorder.events[-1].type == AgentEventType.RUN_COMPLETED
