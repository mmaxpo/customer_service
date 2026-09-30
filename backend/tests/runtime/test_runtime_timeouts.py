import asyncio
import pytest
from pydantic import BaseModel

from app.runtime.engine.executor import execute_workflow_dag
from app.runtime.nodes.registry.builtins import register_node  # adjust if needed


class SleepConfig(BaseModel):
    ms: int = 0


class SleepNode:
    async def run(self, ctx, state, config=None, **kwargs):
        ms = config.ms if config else 0
        await asyncio.sleep(ms / 1000.0)
        return {"status": "ok", "output": f"slept:{ms}"}


@pytest.mark.asyncio
async def test_node_timeout_ms_fails_fast(ctx):
    register_node("test.sleep_timeout", SleepNode, SleepConfig)

    wf = {
        "nodes": [
            {"id": "t", "data": {"nodeType": "trigger.message", "input": "start"}},
            {
                "id": "s",
                "data": {"nodeType": "test.sleep_timeout", "ms": 200, "timeout_ms": 50},
            },
            {"id": "r", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t", "target": "s"},
            {"id": "e2", "source": "s", "target": "r"},
        ],
    }

    out = await execute_workflow_dag(ctx=ctx, workflow=wf, message="")
    assert out["meta"]["status"] == "error"
    assert "node_timeout" in (out["meta"].get("error") or "")
