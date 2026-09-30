import pytest
from app.runtime.engine.executor import execute_workflow_dag
from app.runtime.utils.trace import format_run_trace
from tests.conftest import DummyCtx, InMemoryRunStore


@pytest.mark.asyncio
async def test_resume_after_pause_with_concurrency_does_not_rerun_trigger():
    ctx = DummyCtx()
    ctx.run_store = InMemoryRunStore()
    ctx.extras = {}  # ✅ important: NO resume_input on first run

    wf = {
        "nodes": [
            {"id": "t", "data": {"nodeType": "trigger.message", "input": "start"}},
            {
                "id": "h",
                "data": {
                    "nodeType": "human.approval",
                    "question": "Approve?",
                    "save_as": "approved",
                },
            },
            {
                "id": "s",
                "data": {"nodeType": "set.variable", "key": "x", "value": "OK"},
            },
            {"id": "r", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t", "target": "h"},
            {"id": "e2", "source": "h", "target": "s"},
            {"id": "e3", "source": "s", "target": "r"},
        ],
    }

    # 1) start run -> must pause
    out1 = await execute_workflow_dag(
        ctx=ctx, workflow=wf, message="", strict=True, max_concurrency=4
    )
    assert out1["meta"]["status"] == "paused"
    run_id = out1["meta"]["workflow_run_id"]

    # 2) provide resume payload ONLY now
    ctx.extras = {"resume_input": {"approved": True}}

    out2 = await execute_workflow_dag(
        ctx=ctx,
        workflow=wf,  # ignored anyway because resume loads stored workflow
        message="",
        strict=True,
        resume_workflow_run_id=run_id,
        max_concurrency=4,
    )

    try:
        assert out2["meta"]["status"] == "ok"
        evs = out2["meta"]["events"]

        # attempt=2 should exist
        assert any(
            e.get("event") == "run_resume" and e.get("run_attempt") == 2 for e in evs
        )

        # trigger must NOT rerun on attempt=2
        assert not any(
            e.get("event") == "node_start"
            and e.get("node_id") == "t"
            and e.get("run_attempt") == 2
            for e in evs
        )

        # approval should run again on attempt=2 (it paused, not finished)
        assert any(
            e.get("event") == "node_start"
            and e.get("node_id") == "h"
            and e.get("run_attempt") == 2
            for e in evs
        )

        # downstream nodes SHOULD run on attempt=2
        assert any(
            e.get("event") == "node_start"
            and e.get("node_id") == "s"
            and e.get("run_attempt") == 2
            for e in evs
        )
        assert any(
            e.get("event") == "node_start"
            and e.get("node_id") == "r"
            and e.get("run_attempt") == 2
            for e in evs
        )

    except AssertionError:
        print(format_run_trace(out2["meta"]["events"]))
        raise
