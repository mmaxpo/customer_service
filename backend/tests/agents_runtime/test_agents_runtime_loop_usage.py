from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.agents_runtime.events import AgentEventType
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
    model: str = "fake-model"

    @property
    def usage(self):
        return SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
        )


class FakeLLM:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls = 0

    async def respond(self, *, input_items: list, tools: list[dict]):
        response = self.responses[self.calls]
        self.calls += 1
        return response


@pytest.mark.asyncio
async def test_agent_loop_records_usage_in_events_and_state_meta():
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
    )

    state, recorder = await runner.run(user_input="Say hello")

    llm_finished_events = recorder.by_type(AgentEventType.LLM_CALL_FINISHED)

    assert len(llm_finished_events) == 1

    payload = llm_finished_events[0].payload

    assert payload["usage"]["input_tokens"] == 10
    assert payload["usage"]["output_tokens"] == 5
    assert payload["usage"]["total_tokens"] == 15

    assert payload["run_usage"]["llm_calls"] == 1
    assert payload["run_usage"]["total_tokens"] == 15

    assert state.meta["usage"]["llm_calls"] == 1
    assert state.meta["usage"]["total_tokens"] == 15
