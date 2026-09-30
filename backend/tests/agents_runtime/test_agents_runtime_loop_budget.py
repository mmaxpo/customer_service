from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.agents_runtime.events import AgentEventType
from app.agents_runtime.runner import AgentRunner
from app.agents_runtime.state import AgentStatus
from app.agents_runtime.tools import build_builtin_tool_registry
from app.agents_runtime.usage.budget import UsageBudget


@dataclass
class FakeMessage:
    content: str
    type: str = "message"


@dataclass
class FakeResponse:
    output: list
    output_text: str = "Hello"
    model: str = "fake-model"

    @property
    def usage(self):
        return SimpleNamespace(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
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
async def test_agent_fails_when_token_budget_exceeded():
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
        usage_budget=UsageBudget(max_total_tokens=100),
    )

    state, recorder = await runner.run(user_input="Say hello")

    assert state.status == AgentStatus.FAILED
    assert state.errors
    assert "Token budget exceeded" in state.errors[0].message

    failed_events = recorder.by_type(AgentEventType.RUN_FAILED)
    assert len(failed_events) == 1
    assert "Token budget exceeded" in failed_events[0].payload["error"]


@pytest.mark.asyncio
async def test_agent_fails_when_llm_call_budget_exceeded():
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
        usage_budget=UsageBudget(max_llm_calls=0),
    )

    state, recorder = await runner.run(user_input="Say hello")

    assert state.status == AgentStatus.FAILED
    assert state.errors
    assert "LLM call budget exceeded" in state.errors[0].message

    failed_events = recorder.by_type(AgentEventType.RUN_FAILED)
    assert len(failed_events) == 1
    assert "LLM call budget exceeded" in failed_events[0].payload["error"]
