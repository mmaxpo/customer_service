from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.agents_runtime.runner import AgentRunner
from app.agents_runtime.state import AgentStatus, InMemoryAgentStateStore
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
async def test_agent_runner_persists_state_to_state_store():
    state_store = InMemoryAgentStateStore()

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
        state_store=state_store,
    )

    state, _ = await runner.run(user_input="Say hello")

    stored = await state_store.load(state.agent_run_id)

    assert stored is not None
    assert stored.agent_run_id == state.agent_run_id
    assert stored.status == AgentStatus.COMPLETED
    assert stored.final_output == "Hello"
