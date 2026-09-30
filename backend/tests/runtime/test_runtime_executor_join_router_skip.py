from __future__ import annotations

import pytest
from app.runtime.engine.executor import execute_workflow_dag


@pytest.mark.asyncio
async def test_join_all_waits_for_skipped_branch_chain(ctx):
    wf = {
        "nodes": [
            {"id": "t", "data": {"nodeType": "trigger.message", "input": "billing"}},
            {
                "id": "rt",
                "data": {
                    "nodeType": "router.rules",
                    "default_route": "default",
                    "rules": [{"when": "vars.input == 'billing'", "route": "billing"}],
                },
            },
            {"id": "A", "data": {"nodeType": "set.variable", "key": "a", "value": "A"}},
            {
                "id": "B1",
                "data": {"nodeType": "set.variable", "key": "b1", "value": "B1"},
            },
            {
                "id": "B2",
                "data": {"nodeType": "set.variable", "key": "b2", "value": "B2"},
            },
            {
                "id": "J",
                "data": {"nodeType": "join.all", "mode": "list", "save_as": "joined"},
            },
            {
                "id": "R",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "joined",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "t", "target": "rt"},
            {"id": "e2", "source": "rt", "target": "A", "condition": "billing"},
            {"id": "e3", "source": "rt", "target": "B1", "condition": "refund"},
            {"id": "e4", "source": "B1", "target": "B2"},
            {"id": "e5", "source": "A", "target": "J"},
            {"id": "e6", "source": "B2", "target": "J"},
            {"id": "e7", "source": "J", "target": "R"},
        ],
    }

    out = await execute_workflow_dag(ctx=ctx, workflow=wf, message="")
    assert out["meta"]["status"] == "ok"

    # join should have run, with B-branch producing None because it was skipped
    joined = out["meta"]["outputs_by_node_id"]["J"]
    assert joined == ["A", None]

    # Ensure B1 and B2 were skipped
    events = out["meta"].get("events") or []
    skipped_nodes = {e.get("node_id") for e in events if e.get("event") == "node_skip"}
    assert "B1" in skipped_nodes
    assert "B2" in skipped_nodes
