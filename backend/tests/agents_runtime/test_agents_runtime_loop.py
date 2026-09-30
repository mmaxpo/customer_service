from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from app.agents_runtime.events import AgentEventType
from app.agents_runtime.runner import AgentRunner
from app.agents_runtime.state import AgentStatus
from app.agents_runtime.tools import build_builtin_tool_registry
from tests.agents_runtime.support import build_test_tool_registry


@dataclass
class FakeFunctionCall:
    name: str
    arguments: str
    call_id: str = "call_1"
    type: str = "function_call"


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
async def test_agent_completes_without_tool_call():
    llm = FakeLLM(
        [
            FakeResponse(
                output=[FakeMessage(content="Hello!")],
                output_text="Hello!",
            )
        ]
    )

    runner = AgentRunner(
        llm=llm,
        tool_registry=build_builtin_tool_registry(),
    )

    state, recorder = await runner.run(user_input="Say hello")

    assert state.status == AgentStatus.COMPLETED
    assert state.final_output == "Hello!"
    assert llm.calls == 1

    assert recorder.by_type(AgentEventType.RUN_STARTED)
    assert recorder.by_type(AgentEventType.LLM_CALL_STARTED)
    assert recorder.by_type(AgentEventType.LLM_CALL_FINISHED)
    assert recorder.by_type(AgentEventType.RUN_COMPLETED)


@pytest.mark.asyncio
async def test_agent_executes_tool_then_completes():
    llm = FakeLLM(
        [
            FakeResponse(
                output=[
                    FakeFunctionCall(
                        name="calculator",
                        arguments=json.dumps({"expression": "25 * 19 + 7"}),
                    )
                ],
                output_text="",
            ),
            FakeResponse(
                output=[FakeMessage(content="The result is 482.")],
                output_text="The result is 482.",
            ),
        ]
    )

    runner = AgentRunner(
        llm=llm,
        tool_registry=build_builtin_tool_registry(),
    )

    state, recorder = await runner.run(
        user_input="What is 25 * 19 + 7?",
        tool_names=["calculator"],
    )

    assert state.status == AgentStatus.COMPLETED
    assert state.final_output == "The result is 482."
    assert llm.calls == 2

    tool_finished = recorder.by_type(AgentEventType.TOOL_CALL_FINISHED)

    assert len(tool_finished) == 1
    assert tool_finished[0].payload["tool_name"] == "calculator"
    assert tool_finished[0].payload["result"] == {"result": 482}


@pytest.mark.asyncio
async def test_agent_pauses_for_dangerous_tool():
    llm = FakeLLM(
        [
            FakeResponse(
                output=[
                    FakeFunctionCall(
                        name="dangerous_test_action",
                        arguments=json.dumps(
                            {
                                "resource_id": "ORD-123",
                                "amount": 49.99,
                            }
                        ),
                    )
                ],
                output_text="",
            )
        ]
    )

    runner = AgentRunner(
        llm=llm,
        tool_registry=build_test_tool_registry(),
    )

    state, recorder = await runner.run(
        user_input="Refund order ORD-123 for 49.99",
        tool_names=["dangerous_test_action"],
    )

    assert state.status == AgentStatus.PAUSED
    assert state.pending_approval is not None
    assert state.pending_approval.tool_name == "dangerous_test_action"
    assert state.pending_approval.arguments == {
        "resource_id": "ORD-123",
        "amount": 49.99,
    }

    approval_events = recorder.by_type(AgentEventType.APPROVAL_REQUIRED)

    assert len(approval_events) == 1
    assert approval_events[0].payload["tool_name"] == "dangerous_test_action"


@pytest.mark.asyncio
async def test_agent_fails_on_unknown_tool():
    llm = FakeLLM(
        [
            FakeResponse(
                output=[
                    FakeFunctionCall(
                        name="missing_tool",
                        arguments=json.dumps({"x": 1}),
                    )
                ],
                output_text="",
            )
        ]
    )

    runner = AgentRunner(
        llm=llm,
        tool_registry=build_builtin_tool_registry(),
    )

    state, recorder = await runner.run(
        user_input="Use missing tool",
        tool_names=None,
    )

    assert state.status == AgentStatus.FAILED
    assert state.errors

    failed_events = recorder.by_type(AgentEventType.RUN_FAILED)

    assert len(failed_events) == 1
    assert "Unknown tool" in failed_events[0].payload["error"]


@pytest.mark.asyncio
async def test_agent_fails_after_max_steps():
    llm = FakeLLM(
        [
            FakeResponse(
                output=[
                    FakeFunctionCall(
                        name="echo",
                        arguments=json.dumps({"text": "again"}),
                    )
                ],
                output_text="",
            ),
            FakeResponse(
                output=[
                    FakeFunctionCall(
                        name="echo",
                        arguments=json.dumps({"text": "again"}),
                    )
                ],
                output_text="",
            ),
        ]
    )

    runner = AgentRunner(
        llm=llm,
        tool_registry=build_test_tool_registry(),
        max_steps=2,
    )

    state, recorder = await runner.run(
        user_input="Loop forever",
        tool_names=["echo"],
    )

    assert state.status == AgentStatus.FAILED
    assert state.errors[0].message == "Max steps reached."

    failed_events = recorder.by_type(AgentEventType.RUN_FAILED)
    assert failed_events[0].payload["error"] == "Max steps reached."
