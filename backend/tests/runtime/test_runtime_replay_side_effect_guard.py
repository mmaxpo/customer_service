from __future__ import annotations

from collections import defaultdict

import pytest
from pydantic import BaseModel

from app.runtime.nodes.registry.builtins import register_builtin_nodes
from app.runtime.nodes.builtins.set_variable import SetVariableNode
from app.runtime.engine.executor import execute_workflow_dag
from app.runtime.nodes.registry import register_node
from app.runtime.state.run_state import new_run_state
from tests.conftest import DummyCtx


SIDE_EFFECT_CALLS: dict[str, int] = defaultdict(int)


class DangerousSideEffectConfig(BaseModel):
    nodeType: str = "test.dangerous_side_effect"
    key: str = "dangerous_action_executed"
    value: bool = True
    replay_policy: str | None = None


class DangerousSideEffectNode:
    async def run(self, ctx, state, config=None, **kwargs):
        run_id = str(state["workflow_run_id"])
        SIDE_EFFECT_CALLS[run_id] += 1

        key = getattr(config, "key", "dangerous_action_executed")
        value = getattr(config, "value", True)

        return {
            "status": "ok",
            "output": value,
            "patch": {"vars": {key: value}},
            "meta": {"side_effect": "executed"},
        }


def _register_nodes():
    register_builtin_nodes()
    register_node(
        "test.dangerous_side_effect",
        DangerousSideEffectNode,
        DangerousSideEffectConfig,
    )


def _workflow_with_dangerous_node():
    return {
        "nodes": [
            {
                "id": "trigger",
                "data": {"nodeType": "trigger.message", "input": "start"},
            },
            {
                "id": "safe_set",
                "data": {"nodeType": "set.variable", "key": "a", "value": "A"},
            },
            {
                "id": "dangerous",
                "data": {
                    "nodeType": "test.dangerous_side_effect",
                    "key": "dangerous_action_executed",
                    "value": True,
                    "replay_policy": "skip",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "dangerous_action_executed",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger", "target": "safe_set"},
            {"id": "e2", "source": "safe_set", "target": "dangerous"},
            {"id": "e3", "source": "dangerous", "target": "response"},
        ],
    }


@pytest.mark.asyncio
async def test_replay_from_snapshot_does_not_repeat_dangerous_side_effect_node():
    """
    Harsh production case:

    Replay/debug starts from a snapshot before a dangerous side-effect node.

    Expected:
        - dangerous node is skipped
        - downstream child is skipped because its parent was skipped
        - no external side effect is executed
    """
    _register_nodes()

    original_state = new_run_state("start")
    original_state["workflow_run_id"] = "11111111-1111-1111-1111-111111111111"
    original_state["vars"] = {"input": "start", "a": "A"}
    original_state["results"] = {
        "trigger": "start",
        "safe_set": "A",
    }
    original_state["last"] = "A"
    original_state["meta"]["finished_nodes"] = ["trigger", "safe_set"]
    original_state["meta"]["skipped_nodes"] = []

    ctx = DummyCtx()
    ctx.extras = {}

    result = await execute_workflow_dag(
        ctx=ctx,
        workflow=_workflow_with_dangerous_node(),
        message="",
        strict=True,
        replay_state=original_state,
        replay_parent_workflow_run_id=original_state["workflow_run_id"],
    )

    replay_run_id = str(result["meta"]["workflow_run_id"])

    assert result["meta"]["status"] == "ok"
    assert SIDE_EFFECT_CALLS[replay_run_id] == 0

    replay_meta = result["meta"]["final_state"]["meta"]["replay"]
    skipped = replay_meta["skipped_side_effect_nodes"]

    assert skipped == [
        {
            "node_id": "dangerous",
            "node_type": "test.dangerous_side_effect",
            "policy": "skip",
        }
    ]

    events = result["meta"]["events"]
    assert any(
        event.get("event") == "node_skip"
        and event.get("node_id") == "dangerous"
        and event.get("reason") == "replay_side_effect_blocked"
        for event in events
    )

    assert not any(
        event.get("event") == "node_start" and event.get("node_id") == "dangerous"
        for event in events
    )


@pytest.mark.asyncio
async def test_replay_still_executes_safe_nodes():
    """
    Guard against over-blocking:

    Safe deterministic nodes must still execute during replay.
    """
    _register_nodes()

    workflow = {
        "nodes": [
            {
                "id": "trigger",
                "data": {"nodeType": "trigger.message", "input": "start"},
            },
            {
                "id": "safe_set",
                "data": {"nodeType": "set.variable", "key": "a", "value": "A"},
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "a",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger", "target": "safe_set"},
            {"id": "e2", "source": "safe_set", "target": "response"},
        ],
    }

    original_state = new_run_state("start")
    original_state["workflow_run_id"] = "22222222-2222-2222-2222-222222222222"
    original_state["results"] = {"trigger": "start"}
    original_state["meta"]["finished_nodes"] = ["trigger"]
    original_state["meta"]["skipped_nodes"] = []

    ctx = DummyCtx()
    ctx.extras = {}

    result = await execute_workflow_dag(
        ctx=ctx,
        workflow=workflow,
        message="",
        strict=True,
        replay_state=original_state,
        replay_parent_workflow_run_id=original_state["workflow_run_id"],
    )

    assert result["meta"]["status"] == "ok"
    assert result["answer"] == "A"
    assert result["meta"]["final_state"]["vars"]["a"] == "A"

    events = result["meta"]["events"]
    assert any(
        event.get("event") == "node_start" and event.get("node_id") == "safe_set"
        for event in events
    )
