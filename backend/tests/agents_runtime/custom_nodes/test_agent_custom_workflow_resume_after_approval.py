from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.runtime.engine.executor import execute_workflow_dag
from tests._inmemory_stream_store import InMemoryEventSink, InMemoryRunStore


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
async def test_agent_custom_workflow_resumes_after_approval(ctx):
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

    ctx.tools = SimpleNamespace(llm=fake_llm)

    run_store = InMemoryRunStore()
    ctx.run_store = run_store
    ctx.event_sink = InMemoryEventSink(run_store)
    ctx.extras = {}

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

    paused = await execute_workflow_dag(
        ctx=ctx,
        workflow=workflow,
        message="Refund order ORD-123 for 49.99",
    )

    assert paused["meta"]["status"] == "paused"
    assert paused["meta"]["interrupt"]["tool_name"] == "dangerous_test_action"

    resumed_ctx = ctx
    resumed_ctx.extras = {
        "resume_input": {
            "approved": True,
        }
    }

    resumed = await execute_workflow_dag(
        ctx=resumed_ctx,
        workflow={},  # ignored in resume mode
        message="Refund order ORD-123 for 49.99",
        strict=False,
        resume_workflow_run_id=paused["meta"]["workflow_run_id"],
    )

    assert resumed["meta"]["status"] == "ok"
    assert resumed["answer"] == "Refund created for ORD-123."
    assert fake_llm.calls == 2

    agent_meta = resumed["meta"]["node_meta_by_id"]["agent"]

    assert agent_meta["agent_status"] == "completed"
    assert agent_meta["agent_pending_approval"] is None

    event_types = [event["type"] for event in agent_meta["agent_events"]]

    assert "approval_granted" in event_types
    assert "tool_call_finished" in event_types
    assert "run_completed" in event_types

pytestmark = pytest.mark.usefixtures("install_test_agent_tools")
