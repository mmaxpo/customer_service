import json
from types import SimpleNamespace

import pytest

from app.runtime.engine.executor import execute_workflow_dag
from app.runtime.engine.persistence.memory import InMemoryRunStore, InMemoryEventSink


class FakeText:
    def __init__(self, text: str):
        self.type = "output_text"
        self.text = text


class FakeMessage:
    def __init__(self, content: str):
        self.type = "message"
        self.content = [FakeText(content)]


class FakeFunctionCall:
    def __init__(self, name: str, arguments: str, call_id: str = "call_1"):
        self.type = "function_call"
        self.name = name
        self.arguments = arguments
        self.call_id = call_id


class FakeResponse:
    def __init__(self, output, output_text: str = ""):
        self.output = output
        self.output_text = output_text
        self.usage = None


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def respond(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("FakeLLM has no more responses")
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_shared_workflow_vars_agent_b_reads_agent_a_saved_value(ctx):
    fake_llm = FakeLLM(
        [
            FakeResponse(
                [FakeMessage("customer_intent=refund")], "customer_intent=refund"
            ),
            FakeResponse(
                [FakeMessage("reply=refund policy selected")],
                "reply=refund policy selected",
            ),
        ]
    )
    ctx.tools = SimpleNamespace(llm=fake_llm)

    workflow = {
        "nodes": [
            {
                "id": "trigger",
                "data": {"nodeType": "trigger.message", "input": "I want refund"},
            },
            {
                "id": "agent_a",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "input_from": "last",
                    "tools": [],
                    "save_as": "customer_intent",
                },
            },
            {
                "id": "agent_b",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "input_from": "vars",
                    "input_key": "customer_intent",
                    "tools": [],
                    "save_as": "support_reply",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "support_reply",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger", "target": "agent_a"},
            {"id": "e2", "source": "agent_a", "target": "agent_b"},
            {"id": "e3", "source": "agent_b", "target": "response"},
        ],
    }

    result = await execute_workflow_dag(
        ctx=ctx, workflow=workflow, message="I want refund"
    )

    assert result["meta"]["status"] == "ok"
    assert result["answer"] == "reply=refund policy selected"

    second_call = json.dumps(fake_llm.calls[1], default=str)
    assert "customer_intent=refund" in second_call


@pytest.mark.asyncio
async def test_mixed_agent_then_router_rules_response(ctx):
    fake_llm = FakeLLM(
        [
            FakeResponse([FakeMessage("refund")], "refund"),
        ]
    )
    ctx.tools = SimpleNamespace(llm=fake_llm)

    workflow = {
        "nodes": [
            {
                "id": "trigger",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "Customer wants refund",
                },
            },
            {
                "id": "agent",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "input_from": "last",
                    "tools": [],
                    "save_as": "intent",
                },
            },
            {
                "id": "router",
                "data": {
                    "nodeType": "router.rules",
                    "source": "vars",
                    "key": "intent",
                    "rules": [
                        {"when": "vars.intent == 'refund'", "route": "refund_path"},
                    ],
                    "default_route": "fallback_path",
                },
            },
            {
                "id": "refund_set_answer",
                "data": {
                    "nodeType": "set.variable",
                    "key": "final_answer",
                    "value": "Refund path selected",
                },
            },
            {
                "id": "fallback_set_answer",
                "data": {
                    "nodeType": "set.variable",
                    "key": "final_answer",
                    "value": "Fallback path selected",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "final_answer",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger", "target": "agent"},
            {"id": "e2", "source": "agent", "target": "router"},
            {
                "id": "e3",
                "source": "router",
                "target": "refund_set_answer",
                "data": {"route": "refund_path"},
            },
            {
                "id": "e4",
                "source": "router",
                "target": "fallback_set_answer",
                "data": {"route": "fallback_path"},
            },
            {"id": "e5", "source": "refund_set_answer", "target": "response"},
            {"id": "e6", "source": "fallback_set_answer", "target": "response"},
        ],
    }

    result = await execute_workflow_dag(
        ctx=ctx, workflow=workflow, message="Customer wants refund"
    )

    assert result["meta"]["status"] == "ok"
    assert result["answer"] == "Refund path selected"
    assert result["meta"]["final_state"]["vars"]["route_key"] == "refund_path"


@pytest.mark.asyncio
async def test_parallel_approval_branch_preserves_completed_branch_after_resume(ctx):
    fake_llm = FakeLLM(
        [
            FakeResponse([FakeMessage("safe branch done")], "safe branch done"),
            FakeResponse(
                [
                    FakeFunctionCall(
                        name="dangerous_test_action",
                        arguments=json.dumps({"resource_id": "ORD-123", "amount": 49.99}),
                    )
                ],
                "",
            ),
            FakeResponse([FakeMessage("refund branch done")], "refund branch done"),
        ]
    )
    ctx.tools = SimpleNamespace(llm=fake_llm)
    ctx.run_store = InMemoryRunStore()
    ctx.event_sink = InMemoryEventSink()
    ctx.extras = {}

    workflow = {
        "nodes": [
            {
                "id": "trigger",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "Process support task",
                },
            },
            {
                "id": "safe_agent",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "input_from": "last",
                    "tools": [],
                    "save_as": "safe_result",
                },
            },
            {
                "id": "refund_agent",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "system_prompt": "Call refund tool.",
                    "input_from": "last",
                    "tools": ["dangerous_test_action"],
                    "save_as": "refund_result",
                },
            },
            {"id": "join", "data": {"nodeType": "join.all", "save_as": "joined"}},
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "joined",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger", "target": "safe_agent"},
            {"id": "e2", "source": "trigger", "target": "refund_agent"},
            {"id": "e3", "source": "safe_agent", "target": "join"},
            {"id": "e4", "source": "refund_agent", "target": "join"},
            {"id": "e5", "source": "join", "target": "response"},
        ],
    }

    paused = await execute_workflow_dag(
        ctx=ctx, workflow=workflow, message="Process support task"
    )

    assert paused["meta"]["status"] == "paused"
    ctx.extras = {"resume_input": {"approved": True}}
    resumed = await execute_workflow_dag(
        ctx=ctx,
        workflow=workflow,
        message="Process support task",
        resume_workflow_run_id=paused["meta"]["workflow_run_id"],
    )

    assert resumed["meta"]["status"] == "ok"
    text = json.dumps(resumed, default=str)
    assert "safe branch done" in text
    assert "refund branch done" in text


@pytest.mark.asyncio
async def test_workflow_events_include_child_agent_run_id(ctx):
    fake_llm = FakeLLM(
        [
            FakeResponse([FakeMessage("done")], "done"),
        ]
    )
    ctx.tools = SimpleNamespace(llm=fake_llm)
    ctx.run_store = InMemoryRunStore()
    ctx.event_sink = InMemoryEventSink()

    workflow = {
        "nodes": [
            {
                "id": "trigger",
                "data": {"nodeType": "trigger.message", "input": "start"},
            },
            {
                "id": "agent",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "input_from": "last",
                    "tools": [],
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
            {"id": "e1", "source": "trigger", "target": "agent"},
            {"id": "e2", "source": "agent", "target": "response"},
        ],
    }

    result = await execute_workflow_dag(ctx=ctx, workflow=workflow, message="start")

    assert result["meta"]["status"] == "ok"

    events_text = json.dumps(
        result["meta"]["final_state"]["meta"]["node_meta_by_id"],
        default=str,
    )
    assert "agent_run_id" in events_text

pytestmark = pytest.mark.usefixtures("install_test_agent_tools")
