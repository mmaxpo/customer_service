from __future__ import annotations

import pytest

from app.runtime.engine.executor import execute_workflow_dag


@pytest.mark.asyncio
async def test_executor_router_conditional_skip(ctx):
    wf = {
        "nodes": [
            {
                "id": "t2",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "billing: I was charged twice",
                },
            },
            {
                "id": "rt",
                "data": {
                    "nodeType": "router.rules",
                    "default_route": "default",
                    "rules": [
                        {
                            "when": "vars.input == 'billing: I was charged twice'",
                            "route": "billing",
                        }
                    ],
                },
            },
            {
                "id": "A",
                "data": {
                    "nodeType": "set.variable",
                    "key": "path",
                    "value": "A: billing path ran",
                },
            },
            {
                "id": "B",
                "data": {
                    "nodeType": "set.variable",
                    "key": "path",
                    "value": "B: refund path ran",
                },
            },
            {"id": "r2", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t2", "target": "rt"},
            # ✅ v1 structured when (dropdown-only)
            {
                "id": "e2",
                "source": "rt",
                "target": "A",
                "when": {"eq": ["vars.route_key", "billing"]},
            },
            {
                "id": "e3",
                "source": "rt",
                "target": "B",
                "when": {"eq": ["vars.route_key", "refund"]},
            },
            {"id": "e4", "source": "A", "target": "r2"},
            {"id": "e5", "source": "B", "target": "r2"},
        ],
    }

    out = await execute_workflow_dag(ctx=ctx, workflow=wf, message="")
    meta = out["meta"]

    assert meta["status"] == "ok"
    assert out["answer"] == "A: billing path ran"

    # A ran, B did not
    assert meta["outputs_by_node_id"]["A"] == "A: billing path ran"
    assert (
        "B" not in meta["outputs_by_node_id"]
        or meta["outputs_by_node_id"].get("B") is None
    )

    # skip event exists
    events = meta.get("events") or []
    assert any(
        e.get("event") == "node_skip" and e.get("node_id") == "B" for e in events
    ), events
