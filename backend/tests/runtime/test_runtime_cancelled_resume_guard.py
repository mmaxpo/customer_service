import pytest

from app.runtime.engine.executor import execute_workflow_dag
from tests.conftest import DummyCtx, InMemoryRunStore


@pytest.mark.asyncio
async def test_cancelled_paused_run_cannot_be_resumed_by_old_wait_or_job():
    """
    Production harsh case:

    A workflow pauses for human/wait input. Before the old resume job fires,
    the run is cancelled. The late resume must not execute downstream nodes.

    This protects against dangerous late side effects such as refund/send/reply.
    """
    ctx = DummyCtx()
    ctx.run_store = InMemoryRunStore()
    ctx.extras = {}

    workflow = {
        "nodes": [
            {"id": "t", "data": {"nodeType": "trigger.message"}},
            {
                "id": "h",
                "data": {
                    "nodeType": "human.approval",
                    "question": "Approve?",
                    "save_as": "approved",
                },
            },
            {
                "id": "side_effect",
                "data": {
                    "nodeType": "set.variable",
                    "key": "dangerous_action_executed",
                    "value": True,
                },
            },
            {"id": "r", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t", "target": "h"},
            {"id": "e2", "source": "h", "target": "side_effect"},
            {"id": "e3", "source": "side_effect", "target": "r"},
        ],
    }

    paused = await execute_workflow_dag(
        ctx=ctx,
        workflow=workflow,
        message="start",
        strict=True,
    )

    assert paused["meta"]["status"] == "paused"
    run_id = paused["meta"]["workflow_run_id"]

    # Simulate cancellation that happens before an old wait/job resumes.
    await ctx.run_store.update_run(
        run_id=paused["meta"]["final_state"]["workflow_run_id"],
        status="cancelled",
        state=paused["meta"]["final_state"],
        extra={"reason": "user_cancelled_before_resume_job_fired"},
    )

    ctx.extras = {"resume_input": {"approved": True}}

    resumed = await execute_workflow_dag(
        ctx=ctx,
        workflow={},  # resume loads stored workflow/status
        message="",
        strict=True,
        resume_workflow_run_id=run_id,
    )

    assert resumed["meta"]["status"] == "error"
    assert resumed["meta"]["error"] == "run_cancelled"
    assert resumed["meta"]["current_status"] == "cancelled"

    # The late resume must not run downstream nodes.
    events = paused["meta"]["events"]
    assert not any(
        event.get("event") == "node_start"
        and event.get("node_id") == "side_effect"
        and event.get("run_attempt") == 2
        for event in events
    )
