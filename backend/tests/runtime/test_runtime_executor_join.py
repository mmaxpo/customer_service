# tests/test_runtime_executor_join.py
from __future__ import annotations

import pytest

from app.runtime.engine.executor import execute_workflow_dag


@pytest.mark.asyncio
async def test_executor_join_collects_two_inputs(ctx):
    wf = {
        "nodes": [
            {"id": "t3", "data": {"nodeType": "trigger.message", "input": "start"}},
            {
                "id": "task1",
                "data": {"nodeType": "set.variable", "key": "o1", "value": "out1"},
            },
            {
                "id": "task2",
                "data": {"nodeType": "set.variable", "key": "o2", "value": "out2"},
            },
            {
                "id": "j1",
                "data": {
                    "nodeType": "join.all",
                    "mode": "concat_text",
                    "separator": " | ",
                },
            },
            {"id": "r3", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t3", "target": "task1"},
            {"id": "e2", "source": "t3", "target": "task2"},
            {"id": "e3", "source": "task1", "target": "j1"},
            {"id": "e4", "source": "task2", "target": "j1"},
            {"id": "e5", "source": "j1", "target": "r3"},
        ],
    }

    out = await execute_workflow_dag(ctx=ctx, workflow=wf, message="")
    meta = out["meta"]

    assert meta["status"] == "ok"
    assert out["answer"] == "out1 | out2"

    assert meta["outputs_by_node_id"]["j1"] == "out1 | out2"
    assert meta["node_meta_by_id"]["j1"]["joined"] == 2
