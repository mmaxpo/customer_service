import pytest
from app.runtime.engine.executor import execute_workflow_dag


@pytest.mark.asyncio
async def test_loop_then_join_collects_each_iteration(ctx):
    # Requires your control.loop node to increment vars.loop_count and route continue/stop
    wf = {
        "nodes": [
            {"id": "t", "data": {"nodeType": "trigger.message", "input": "hi"}},
            {"id": "a", "data": {"nodeType": "set.variable", "key": "x", "value": "A"}},
            {
                "id": "loop",
                "data": {
                    "nodeType": "control.loop",
                    "max_iters": 3,
                    "reset_node_ids": ["a"],
                },
            },
            {
                "id": "j",
                "data": {"nodeType": "join.all", "mode": "list", "save_as": "joined"},
            },
            {
                "id": "r",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "joined",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "t", "target": "a"},
            {"id": "e2", "source": "a", "target": "loop"},
            {
                "id": "e3",
                "source": "loop",
                "target": "a",
                "when": {"eq": ["vars.route_key", "continue"]},
            },
            {
                "id": "e4",
                "source": "loop",
                "target": "j",
                "when": {"eq": ["vars.route_key", "stop"]},
            },
            {"id": "e5", "source": "j", "target": "r"},
        ],
    }

    out = await execute_workflow_dag(ctx=ctx, workflow=wf, message="")
    assert out["meta"]["status"] == "ok"
    assert out["meta"]["final_state"]["vars"]["loop_count"] == 3
