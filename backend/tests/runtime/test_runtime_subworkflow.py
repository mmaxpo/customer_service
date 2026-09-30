from __future__ import annotations

import pytest
from app.runtime.engine.executor import execute_workflow_dag


@pytest.mark.asyncio
async def test_subworkflow_call(ctx):
    # child workflow (inline)
    child = {
        "nodes": [
            {"id": "t", "data": {"nodeType": "trigger.message", "input": "IGNORED"}},
            {
                "id": "s",
                "data": {"nodeType": "set.variable", "key": "x", "value": "ok"},
            },
            {"id": "r", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t", "target": "s"},
            {"id": "e2", "source": "s", "target": "r"},
        ],
    }

    # parent workflow calls child
    parent = {
        "nodes": [
            {
                "id": "tp",
                "data": {"nodeType": "trigger.message", "input": "hello-from-parent"},
            },
            {
                "id": "sub",
                "data": {
                    "nodeType": "subworkflow.call",
                    "workflow": child,  # ✅ inline JSON
                    "input_from": "last",  # feed parent.last into child trigger
                    "include_child_meta": False,
                    "save_as": "child_answer",
                },
            },
            {
                "id": "rp",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "child_answer",
                },
            },
        ],
        "edges": [
            {"id": "p1", "source": "tp", "target": "sub"},
            {"id": "p2", "source": "sub", "target": "rp"},
        ],
    }

    out = await execute_workflow_dag(ctx=ctx, workflow=parent, message="")
    assert out["meta"]["status"] == "ok"
    assert out["answer"] == "ok"
