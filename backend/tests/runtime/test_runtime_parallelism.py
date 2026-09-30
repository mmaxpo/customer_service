from __future__ import annotations

import time
import asyncio
import pytest

from app.runtime.nodes.registry import register_node
from pydantic import BaseModel
from app.runtime.engine.executor import execute_workflow_dag


class SleepConfig(BaseModel):
    node_type: str = "test.sleep"
    ms: int = 200


class SleepNode:
    async def run(self, ctx, state, config: SleepConfig):
        await asyncio.sleep(config.ms / 1000.0)
        return {"patch": {}, "output": f"slept:{config.ms}", "meta": {}}


@pytest.mark.asyncio
async def test_parallel_two_nodes_faster(ctx):
    register_node("test.sleep", SleepNode, SleepConfig)

    wf = {
        "nodes": [
            {"id": "t", "data": {"nodeType": "trigger.message", "input": "hi"}},
            {"id": "s1", "data": {"nodeType": "test.sleep", "ms": 250}},
            {"id": "s2", "data": {"nodeType": "test.sleep", "ms": 250}},
            {"id": "j", "data": {"nodeType": "join.all", "mode": "list"}},
            {"id": "r", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t", "target": "s1"},
            {"id": "e2", "source": "t", "target": "s2"},
            {"id": "e3", "source": "s1", "target": "j"},
            {"id": "e4", "source": "s2", "target": "j"},
            {"id": "e5", "source": "j", "target": "r"},
        ],
    }

    t0 = time.monotonic()
    out = await execute_workflow_dag(
        ctx=ctx, workflow=wf, message="", max_concurrency=2
    )
    dt = time.monotonic() - t0

    assert out["meta"]["status"] == "ok"
    # sequential would be ~0.5s, parallel should be notably less (allow slack)
    assert dt < 0.45
