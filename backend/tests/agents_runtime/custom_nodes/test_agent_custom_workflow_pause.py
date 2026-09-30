from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.runtime.engine.executor import execute_workflow_dag


@dataclass
class FakeFunctionCall:
    name: str
    arguments: str
    call_id: str = "call_1"
    type: str = "function_call"


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
async def test_agent_custom_workflow_pauses_for_dangerous_tool(ctx):
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

    ctx.tools = SimpleNamespace(llm=fake_llm)

    workflow = {
        "nodes": [
            {
                "id": "trigger",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "Refund order ORD-123 for 49.99",
                },
            },
            {
                "id": "agent",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "backend": "pure",
                    "pattern": "tool_agent",
                    "system_prompt": "You are a careful AI agent. Use tools when needed.",
                    "input_from": "last",
                    "tools": ["dangerous_test_action"],
                    "max_steps": 5,
                    "save_as": "refund_result",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "refund_result",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger", "target": "agent"},
            {"id": "e2", "source": "agent", "target": "response"},
        ],
    }

    result = await execute_workflow_dag(
        ctx=ctx,
        workflow=workflow,
        message="Refund order ORD-123 for 49.99",
    )

    assert result["meta"]["status"] == "paused"

    interrupt = result["meta"]["interrupt"]

    assert interrupt["kind"] == "approval"
    assert interrupt["node_type"] == "agent.custom"
    assert interrupt["tool_name"] == "dangerous_test_action"
    assert interrupt["arguments"] == {
        "resource_id": "ORD-123",
        "amount": 49.99,
    }

pytestmark = pytest.mark.usefixtures("install_test_agent_tools")
