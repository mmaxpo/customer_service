import pytest
from app.runtime.engine.executor import execute_workflow_dag
from app.runtime.utils.trace import format_run_trace


@pytest.mark.asyncio
async def test_join_order_deterministic_even_if_edges_shuffled(ctx):
    wf = {
        "nodes": [
            {"id": "t", "data": {"nodeType": "trigger.message", "input": "start"}},
            {
                "id": "a",
                "data": {"nodeType": "set.variable", "key": "o1", "value": "A"},
            },
            {
                "id": "b",
                "data": {"nodeType": "set.variable", "key": "o2", "value": "B"},
            },
            {
                "id": "j",
                "data": {
                    "nodeType": "join.all",
                    "mode": "concat_text",
                    "separator": "|",
                },
            },
            {"id": "r", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e4", "source": "b", "target": "j"},
            {"id": "e2", "source": "t", "target": "b"},
            {"id": "e5", "source": "j", "target": "r"},
            {"id": "e3", "source": "a", "target": "j"},
            {"id": "e1", "source": "t", "target": "a"},
        ],
    }

    out = await execute_workflow_dag(ctx=ctx, workflow=wf, message="")
    assert out["meta"]["status"] == "ok"

    try:
        assert out["answer"] in ("A|B", "A | B")
    except AssertionError:
        print(format_run_trace(out["meta"]["events"]))
        raise
