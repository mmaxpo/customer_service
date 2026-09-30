from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from tests.agents_runtime.support import (
    build_test_tool_registry,
)

from app.agents_runtime.config import AgentCustomConfig
from app.runtime.nodes.builtins.agent_custom import AgentCustomNode


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
async def test_agent_custom_node_completes_with_direct_answer():
    ctx = SimpleNamespace(
        user_id="user-1",
        thread_id="thread-1",
        run_id="workflow-run-1",
        tools=SimpleNamespace(
            llm=FakeLLM(
                [
                    FakeResponse(
                        output=[FakeMessage(content="Hello from agent.")],
                        output_text="Hello from agent.",
                    )
                ]
            )
        ),
    )

    state = {
        "vars": {
            "input": "Say hello",
        },
        "last": "Say hello",
    }

    data = {
        "node_type": "agent.custom",
        "system_prompt": "You are helpful.",
        "input_from": "last",
        "tools": [],
        "max_steps": 5,
        "save_as": "agent_result",
    }

    result = await AgentCustomNode().run(ctx, state, AgentCustomConfig(**data))

    assert result["output"] == "Hello from agent."
    assert result["patch"]["vars"]["agent_result"] == "Hello from agent."
    assert result["meta"]["agent_status"] == "completed"
    assert result["meta"]["agent_steps"] == 1
    assert result["meta"]["agent_errors"] == []


@pytest.mark.asyncio
async def test_agent_custom_node_executes_calculator_tool():
    fake_llm = FakeLLM(
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

    ctx = SimpleNamespace(
        user_id="user-1",
        thread_id="thread-1",
        run_id="workflow-run-1",
        tools=SimpleNamespace(llm=fake_llm),
    )

    state = {
        "vars": {
            "input": "What is 25 * 19 + 7?",
        },
        "last": "What is 25 * 19 + 7?",
    }

    data = {
        "node_type": "agent.custom",
        "system_prompt": "Use tools when needed.",
        "input_from": "last",
        "tools": ["calculator"],
        "max_steps": 5,
        "save_as": "math_answer",
    }

    result = await AgentCustomNode().run(ctx, state, AgentCustomConfig(**data))

    assert result["output"] == "The result is 482."
    assert result["patch"]["vars"]["math_answer"] == "The result is 482."
    assert result["meta"]["agent_status"] == "completed"
    assert fake_llm.calls == 2

    events = result["meta"]["agent_events"]
    event_types = [event["type"] for event in events]

    assert "tool_call_started" in event_types
    assert "tool_call_finished" in event_types


@pytest.mark.asyncio
async def test_agent_custom_node_pauses_for_refund_tool(monkeypatch):
    monkeypatch.setattr(
        "app.runtime.nodes.builtins.agent_custom.build_builtin_tool_registry",
        build_test_tool_registry,
    )

    fake_llm = FakeLLM(
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

    ctx = SimpleNamespace(
        user_id="user-1",
        thread_id="thread-1",
        run_id="workflow-run-1",
        tools=SimpleNamespace(llm=fake_llm),
    )

    state = {
        "vars": {
            "input": "Refund order ORD-123 for 49.99",
        },
        "last": "Refund order ORD-123 for 49.99",
    }

    data = {
        "node_type": "agent.custom",
        "system_prompt": "Use tools when needed.",
        "input_from": "last",
        "tools": ["dangerous_test_action"],
        "max_steps": 5,
        "save_as": "refund_result",
    }

    result = await AgentCustomNode().run(ctx, state, AgentCustomConfig(**data))

    assert result["status"] == "paused"
    assert result["output"] is None
    snapshot_key = result["interrupt"]["snapshot_key"]

    assert snapshot_key in result["patch"]["vars"]
    assert result["patch"]["vars"][snapshot_key]["status"] == "paused"
    assert (
        result["patch"]["vars"][snapshot_key]["pending_approval"]["tool_name"]
        == "dangerous_test_action"
    )

    assert result["interrupt"]["kind"] == "approval"
    assert result["interrupt"]["node_type"] == "agent.custom"
    assert result["interrupt"]["tool_name"] == "dangerous_test_action"

    assert result["meta"]["paused"] is True
    assert result["meta"]["agent_status"] == "paused"
    assert result["meta"]["agent_pending_approval"]["tool_name"] == "dangerous_test_action"

pytestmark = pytest.mark.usefixtures("install_test_agent_tools")
