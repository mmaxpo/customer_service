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
async def test_agent_custom_resumes_after_approval(monkeypatch):
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
            ),
            FakeResponse(
                output=[FakeMessage(content="Refund created for ORD-123.")],
                output_text="Refund created for ORD-123.",
            ),
        ]
    )

    config = AgentCustomConfig(
        node_type="agent.custom",
        system_prompt="Use tools when needed.",
        input_from="last",
        tools=["dangerous_test_action"],
        max_steps=5,
        save_as="refund_result",
    )

    pause_ctx = SimpleNamespace(
        user_id="user-1",
        thread_id="thread-1",
        run_id="workflow-run-1",
        extras={},
        tools=SimpleNamespace(llm=fake_llm),
    )

    initial_state = {
        "vars": {
            "input": "Refund order ORD-123 for 49.99",
        },
        "last": "Refund order ORD-123 for 49.99",
    }

    paused_result = await AgentCustomNode().run(
        pause_ctx,
        initial_state,
        config,
    )

    assert paused_result["status"] == "paused"

    snapshot_key = paused_result["interrupt"]["snapshot_key"]
    snapshot = paused_result["patch"]["vars"][snapshot_key]

    resume_ctx = SimpleNamespace(
        user_id="user-1",
        thread_id="thread-1",
        run_id="workflow-run-1",
        extras={
            "resume_input": {
                "approved": True,
            }
        },
        tools=SimpleNamespace(llm=fake_llm),
    )

    resumed_state = {
        "vars": {
            "input": "Refund order ORD-123 for 49.99",
            snapshot_key: snapshot,
        },
        "last": "Refund order ORD-123 for 49.99",
    }

    resumed_result = await AgentCustomNode().run(
        resume_ctx,
        resumed_state,
        config,
    )

    assert resumed_result["output"] == "Refund created for ORD-123."
    assert (
        resumed_result["patch"]["vars"]["refund_result"]
        == "Refund created for ORD-123."
    )
    assert resumed_result["patch"]["vars"][snapshot_key] is None

    assert resumed_result["meta"]["agent_status"] == "completed"
    assert resumed_result["meta"]["agent_pending_approval"] is None

    event_types = [event["type"] for event in resumed_result["meta"]["agent_events"]]

    assert "approval_granted" in event_types
    assert "tool_call_finished" in event_types
    assert "run_completed" in event_types

    assert fake_llm.calls == 2

pytestmark = pytest.mark.usefixtures("install_test_agent_tools")
