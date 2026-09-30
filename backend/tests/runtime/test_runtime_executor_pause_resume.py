from __future__ import annotations

import uuid
import pytest

from app.runtime.nodes.registry.builtins import register_builtin_nodes
from app.runtime.engine.executor import execute_workflow_dag
from app.runtime.engine.persistence.memory import InMemoryRunStore, InMemoryEventSink


class DummyCtx:
    def __init__(self):
        self.request = None
        self.user_id = uuid.uuid4()
        self.thread_id = uuid.uuid4()
        self.db = None
        self.extras = {}

        register_builtin_nodes()
        self.run_store = InMemoryRunStore()
        self.event_sink = InMemoryEventSink()

    @property
    def app(self):
        class _App:
            state = type("S", (), {})()

        return _App()


@pytest.mark.asyncio
async def test_pause_then_resume_continues_without_rerun():
    ctx = DummyCtx()

    wf = {
        "nodes": [
            {"id": "t1", "data": {"nodeType": "trigger.message", "input": "start"}},
            {
                "id": "h1",
                "data": {
                    "nodeType": "human.approval",
                    "question": "Approve?",
                    "save_as": "approved",
                },
            },
            {
                "id": "s1",
                "data": {"nodeType": "set.variable", "key": "result", "value": "OK"},
            },
            {"id": "r1", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t1", "target": "h1"},
            {"id": "e2", "source": "h1", "target": "s1"},
            {"id": "e3", "source": "s1", "target": "r1"},
        ],
    }

    out1 = await execute_workflow_dag(ctx=ctx, workflow=wf, message="", strict=True)
    assert out1["meta"]["status"] == "paused"
    run_id = out1["meta"]["workflow_run_id"]
    assert run_id

    # resume
    ctx.extras["resume_input"] = {"approved": True}

    out2 = await execute_workflow_dag(
        ctx=ctx,
        workflow={},  # ignored in resume mode
        message="",
        strict=False,  # IMPORTANT: workflow is empty here
        resume_workflow_run_id=run_id,
    )

    assert out2["meta"]["status"] == "ok"
    assert out2["meta"]["final_state"]["vars"]["approved"] is True
    assert out2["meta"]["final_state"]["vars"]["result"] == "OK"

    # ✅ key check: trigger shouldn't run twice after resume patch
    events = out2["meta"].get("events") or []
    trigger_starts = [
        e for e in events if e.get("event") == "node_start" and e.get("node_id") == "t1"
    ]
    assert len(trigger_starts) == 1
