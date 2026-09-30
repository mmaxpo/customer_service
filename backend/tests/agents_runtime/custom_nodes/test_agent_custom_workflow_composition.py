import json
from types import SimpleNamespace

import pytest

from app.runtime.engine.executor import execute_workflow_dag


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
async def test_sequence_agents_agent_a_output_feeds_agent_b(ctx):
    fake_llm = FakeLLM(
        [
            FakeResponse(
                output=[FakeMessage("intent=refund")],
                output_text="intent=refund",
            ),
            FakeResponse(
                output=[FakeMessage("final=refund workflow selected")],
                output_text="final=refund workflow selected",
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
                    "input": "Customer wants a refund",
                },
            },
            {
                "id": "agent_a",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "system_prompt": "Extract customer intent.",
                    "input_from": "last",
                    "tools": [],
                    "max_steps": 3,
                    "save_as": "intent_result",
                },
            },
            {
                "id": "agent_b",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "system_prompt": "Choose workflow from intent.",
                    "input_from": "vars",
                    "input_key": "intent_result",
                    "tools": [],
                    "max_steps": 3,
                    "save_as": "decision_result",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "decision_result",
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
        ctx=ctx,
        workflow=workflow,
        message="Customer wants a refund",
    )

    assert result["meta"]["status"] == "ok"
    assert result["answer"] == "final=refund workflow selected"

    second_call_input = json.dumps(fake_llm.calls[1], default=str)
    assert "intent=refund" in second_call_input


@pytest.mark.asyncio
async def test_parallel_agents_join_results(ctx):
    fake_llm = FakeLLM(
        [
            FakeResponse(
                output=[FakeMessage("sentiment=angry")], output_text="sentiment=angry"
            ),
            FakeResponse(
                output=[FakeMessage("priority=high")], output_text="priority=high"
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
                    "input": "Order is late and customer is angry",
                },
            },
            {
                "id": "sentiment_agent",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "system_prompt": "Detect sentiment.",
                    "input_from": "last",
                    "tools": [],
                    "max_steps": 3,
                    "save_as": "sentiment",
                },
            },
            {
                "id": "priority_agent",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "system_prompt": "Detect priority.",
                    "input_from": "last",
                    "tools": [],
                    "max_steps": 3,
                    "save_as": "priority",
                },
            },
            {
                "id": "join",
                "data": {
                    "nodeType": "join.all",
                    "save_as": "joined",
                },
            },
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
            {"id": "e1", "source": "trigger", "target": "sentiment_agent"},
            {"id": "e2", "source": "trigger", "target": "priority_agent"},
            {"id": "e3", "source": "sentiment_agent", "target": "join"},
            {"id": "e4", "source": "priority_agent", "target": "join"},
            {"id": "e5", "source": "join", "target": "response"},
        ],
    }

    result = await execute_workflow_dag(
        ctx=ctx,
        workflow=workflow,
        message="Order is late and customer is angry",
    )

    assert result["meta"]["status"] == "ok"

    text = json.dumps(result, default=str)
    assert "sentiment=angry" in text
    assert "priority=high" in text


@pytest.mark.asyncio
async def test_two_agent_nodes_have_different_agent_run_ids(ctx):
    fake_llm = FakeLLM(
        [
            FakeResponse(output=[FakeMessage("A done")], output_text="A done"),
            FakeResponse(output=[FakeMessage("B done")], output_text="B done"),
        ]
    )
    ctx.tools = SimpleNamespace(llm=fake_llm)

    workflow = {
        "nodes": [
            {
                "id": "trigger",
                "data": {"nodeType": "trigger.message", "input": "start"},
            },
            {
                "id": "agent_a",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "input_from": "last",
                    "tools": [],
                    "save_as": "a",
                },
            },
            {
                "id": "agent_b",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "input_from": "vars",
                    "input_key": "a",
                    "tools": [],
                    "save_as": "b",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "b",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger", "target": "agent_a"},
            {"id": "e2", "source": "agent_a", "target": "agent_b"},
            {"id": "e3", "source": "agent_b", "target": "response"},
        ],
    }

    result = await execute_workflow_dag(ctx=ctx, workflow=workflow, message="start")

    assert result["meta"]["status"] == "ok"

    text = json.dumps(result, default=str)
    # agent.custom result metadata should contain agent_run_id twice
    assert text.count("agent_run_id") >= 2


@pytest.mark.asyncio
async def test_agent_custom_receives_parent_workflow_run_id(ctx):
    fake_llm = FakeLLM(
        [
            FakeResponse(output=[FakeMessage("done")], output_text="done"),
        ]
    )
    ctx.tools = SimpleNamespace(llm=fake_llm)

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
    workflow_run_id = result["meta"]["workflow_run_id"]

    text = json.dumps(result, default=str)
    assert workflow_run_id in text
