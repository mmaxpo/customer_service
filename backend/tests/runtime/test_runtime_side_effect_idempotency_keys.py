from __future__ import annotations

from collections import defaultdict

import pytest
from pydantic import BaseModel, Field

from app.runtime.nodes.registry.builtins import register_builtin_nodes
from app.runtime.engine.executor import execute_workflow_dag
from app.runtime.nodes.registry import register_node
from tests.conftest import DummyCtx


CALL_KEYS: dict[str, list[str | None]] = defaultdict(list)


class FlakyExternalActionConfig(BaseModel):
    node_type: str = "test.flaky_external_action"
    retries: int = 1
    retry_backoff_ms: int = 1
    side_effect: bool = True
    save_as: str = "external_action"


class FlakyExternalActionNode:
    async def run(self, ctx, state, config):
        run_id = str(state["workflow_run_id"])
        key = ((getattr(ctx, "node_data", None) or {}).get("_runtime") or {}).get(
            "idempotency_key"
        )
        CALL_KEYS[run_id].append(key)

        if len(CALL_KEYS[run_id]) == 1:
            raise RuntimeError("simulated crash/timeout after external attempt")

        return {
            "output": {"ok": True, "idempotency_key": key},
            "patch": {
                "vars": {
                    config.save_as: {"ok": True, "idempotency_key": key},
                },
                "last": {"ok": True, "idempotency_key": key},
            },
            "meta": {"idempotency_key": key},
        }


def _register_nodes():
    register_builtin_nodes()
    register_node(
        "test.flaky_external_action",
        FlakyExternalActionNode,
        FlakyExternalActionConfig,
    )


@pytest.mark.asyncio
async def test_side_effect_node_retries_reuse_same_idempotency_key():
    """
    Harsh production case:

    External side-effect attempt fails locally and node retry runs again.

    Expected:
      - retry receives the same idempotency key
      - external provider can safely dedupe repeated attempt
    """
    _register_nodes()

    workflow = {
        "nodes": [
            {"id": "t", "data": {"nodeType": "trigger.message"}},
            {
                "id": "external",
                "data": {
                    "nodeType": "test.flaky_external_action",
                    "side_effect": True,
                    "retries": 1,
                    "retry_backoff_ms": 1,
                },
            },
            {
                "id": "r",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "external_action",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "t", "target": "external"},
            {"id": "e2", "source": "external", "target": "r"},
        ],
    }

    ctx = DummyCtx()
    ctx.extras = {}

    result = await execute_workflow_dag(
        ctx=ctx,
        workflow=workflow,
        message="start",
        strict=True,
    )

    assert result["meta"]["status"] == "ok"

    run_id = result["meta"]["workflow_run_id"]
    keys = CALL_KEYS[str(run_id)]

    assert len(keys) == 2
    assert keys[0] is not None
    assert keys[0] == keys[1]
    assert (
        result["meta"]["final_state"]["vars"]["external_action"]["idempotency_key"]
        == keys[0]
    )


@pytest.mark.asyncio
async def test_safe_node_does_not_receive_side_effect_idempotency_key():
    """
    Guard against over-applying idempotency metadata to deterministic nodes.
    """
    _register_nodes()

    workflow = {
        "nodes": [
            {"id": "t", "data": {"nodeType": "trigger.message"}},
            {
                "id": "s",
                "data": {"nodeType": "set.variable", "key": "x", "value": "safe"},
            },
            {
                "id": "r",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "x",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "t", "target": "s"},
            {"id": "e2", "source": "s", "target": "r"},
        ],
    }

    ctx = DummyCtx()
    ctx.extras = {}

    result = await execute_workflow_dag(
        ctx=ctx,
        workflow=workflow,
        message="start",
        strict=True,
    )

    assert result["meta"]["status"] == "ok"
    assert result["answer"] == "safe"
