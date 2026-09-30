import asyncio
import json
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.runtime.engine.executor import execute_workflow_dag
from tests.conftest import DummyCtx, InMemoryRunStore


class AtomicClaimingRunStore(InMemoryRunStore):
    async def claim_run_for_resume(self, *, run_id):
        saved = await self.load_run(run_id=run_id)
        if not saved or saved.get("status") != "paused":
            return None
        await self.update_run(
            run_id=run_id,
            status="running",
            state=saved["state"],
            extra={"claimed_for_resume": True},
        )
        return saved


TOOL_CALLS = {"dangerous_test_action": 0}


@dataclass
class FakeFunctionCall:
    name: str
    arguments: str
    call_id: str = "call_refund_1"
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
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0

    async def respond(self, *, input_items: list, tools: list[dict]):
        response = self.responses[self.calls]
        self.calls += 1
        return response


def _workflow():
    return {
        "nodes": [
            {"id": "trigger", "data": {"nodeType": "trigger.message"}},
            {
                "id": "agent",
                "data": {
                    "nodeType": "agent.custom",
                    "node_type": "agent.custom",
                    "backend": "pure",
                    "pattern": "tool_agent",
                    "system_prompt": "Use the refund tool.",
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


@pytest.mark.asyncio
async def test_duplicate_agent_custom_approval_resume_executes_dangerous_tool_once():
    """
    Harsh production case:

    Two approval/resume requests arrive for the same paused workflow agent.

    Expected:
      - one resume claims the paused workflow run
      - one resume is rejected
      - dangerous agent tool executes once
    """
    TOOL_CALLS["dangerous_test_action"] = 0

    async def dangerous_test_action(resource_id: str, amount: float):
        TOOL_CALLS["dangerous_test_action"] += 1
        await asyncio.sleep(0.02)
        return {"status": "refunded", "resource_id": resource_id, "amount": amount}

    fake_llm = FakeLLM(
        [
            FakeResponse(
                output=[
                    FakeFunctionCall(
                        name="dangerous_test_action",
                        arguments=json.dumps({"resource_id": "ORD-123", "amount": 49.99}),
                    )
                ],
                output_text="",
            ),
            FakeResponse(
                output=[FakeMessage("Refund created for ORD-123.")],
                output_text="Refund created for ORD-123.",
            ),
        ]
    )

    run_store = AtomicClaimingRunStore()

    pause_ctx = DummyCtx()
    pause_ctx.run_store = run_store
    pause_ctx.extras = {}
    pause_ctx.tools = SimpleNamespace(llm=fake_llm)

    registry_tools = pause_ctx.tools
    registry_tools.dangerous_test_action = dangerous_test_action

    paused = await execute_workflow_dag(
        ctx=pause_ctx,
        workflow=_workflow(),
        message="Refund order ORD-123 for 49.99",
        strict=False,
    )

    assert paused["meta"]["status"] == "paused"
    run_id = paused["meta"]["workflow_run_id"]

    async def approve_once():
        ctx = DummyCtx()
        ctx.run_store = run_store
        ctx.tools = registry_tools
        ctx.extras = {"resume_input": {"approved": True}}

        return await execute_workflow_dag(
            ctx=ctx,
            workflow={},
            message="Refund order ORD-123 for 49.99",
            strict=False,
            resume_workflow_run_id=run_id,
        )

    first, second = await asyncio.gather(approve_once(), approve_once())

    statuses = [first["meta"]["status"], second["meta"]["status"]]

    assert statuses.count("ok") == 1
    assert statuses.count("error") == 1
    ok_result = first if first["meta"]["status"] == "ok" else second
    assert "Refund created for ORD-123" in str(ok_result)

    error_result = first if first["meta"]["status"] == "error" else second
    assert error_result["meta"]["error"] in {
        "run_already_resuming",
        "run_not_paused",
    }

pytestmark = pytest.mark.usefixtures("install_test_agent_tools")
