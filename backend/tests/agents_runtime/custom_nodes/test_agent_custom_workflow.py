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
async def test_agent_custom_inside_workflow(ctx):
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
                output=[FakeMessage(content="482")],
                output_text="482",
            ),
        ]
    )

    ctx.tools = SimpleNamespace(llm=fake_llm)

    workflow = {
        "nodes": [
            {
                "id": "trigger",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "What is 25 * 19 + 7?",
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
                    "input_key": "input",
                    "tools": ["calculator"],
                    "max_steps": 5,
                    "save_as": "agent_result",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "agent_result",
                },
            },
        ],
        "edges": [
            {
                "id": "e1",
                "source": "trigger",
                "target": "agent",
            },
            {
                "id": "e2",
                "source": "agent",
                "target": "response",
            },
        ],
    }

    result = await execute_workflow_dag(
        ctx=ctx,
        workflow=workflow,
        message="What is 25 * 19 + 7?",
    )

    assert result["meta"]["status"] == "ok"
    assert result["answer"] == "482"
    assert fake_llm.calls == 2

    assert result["meta"]["outputs_by_node_id"]["agent"] == "482"

    agent_meta = result["meta"]["node_meta_by_id"]["agent"]

    assert agent_meta["agent_status"] == "completed"
    assert agent_meta["agent_steps"] == 2

    event_types = [event["type"] for event in agent_meta["agent_events"]]

    assert "tool_call_started" in event_types
    assert "tool_call_finished" in event_types
    assert "run_completed" in event_types
