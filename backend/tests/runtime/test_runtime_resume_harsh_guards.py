from __future__ import annotations

import asyncio
import copy
from collections import defaultdict
from uuid import UUID

import pytest
from pydantic import BaseModel

from app.runtime.nodes.registry.builtins import register_node
from app.runtime.engine.executor import execute_workflow_dag
from tests.conftest import DummyCtx


SIDE_EFFECT_CALLS: dict[str, int] = defaultdict(int)


class AtomicClaimingRunStore:
    """
    In-memory test store that models the production Postgres resume claim.

    The important behavior is atomic:
        paused -> running

    Only one resume worker can win that transition.
    """

    def __init__(self):
        self._runs = {}

    async def create_run(
        self,
        *,
        run_id,
        user_id=None,
        thread_id=None,
        workflow=None,
        state=None,
    ):
        self._runs.setdefault(
            run_id,
            {
                "status": "running",
                "workflow": copy.deepcopy(workflow),
                "state": copy.deepcopy(state),
            },
        )

    async def load_run(self, *, run_id):
        row = self._runs.get(run_id)
        return copy.deepcopy(row) if row else None

    async def claim_run_for_resume(self, *, run_id):
        row = self._runs.get(run_id)

        if not row or row["status"] != "paused":
            return None

        row["status"] = "running"
        return copy.deepcopy(row)

    async def update_run(self, *, run_id, status, state, extra=None):
        row = self._runs.setdefault(
            run_id,
            {"workflow": None, "state": None, "status": None},
        )
        row["status"] = status
        row["state"] = copy.deepcopy(state)
        if extra is not None:
            row["extra"] = copy.deepcopy(extra)


class SlowSideEffectConfig(BaseModel):
    key: str = "dangerous_action"
    value: bool = True
    sleep_ms: int = 25


class SlowSideEffectNode:
    async def run(self, ctx, state, config=None, **kwargs):
        cfg = config or SlowSideEffectConfig()
        run_id = str(state["workflow_run_id"])

        SIDE_EFFECT_CALLS[run_id] += 1

        await asyncio.sleep(cfg.sleep_ms / 1000)

        return {
            "status": "ok",
            "output": cfg.value,
            "set": {cfg.key: cfg.value},
        }


def _register_test_node():
    register_node(
        "test.slow_side_effect_once",
        SlowSideEffectNode,
        SlowSideEffectConfig,
    )


def _approval_workflow():
    return {
        "nodes": [
            {"id": "t", "data": {"nodeType": "trigger.message", "input": "start"}},
            {
                "id": "h",
                "data": {
                    "nodeType": "human.approval",
                    "question": "Approve dangerous action?",
                    "save_as": "approved",
                },
            },
            {
                "id": "dangerous_action",
                "data": {
                    "nodeType": "test.slow_side_effect_once",
                    "key": "dangerous_action_executed",
                    "value": True,
                    "sleep_ms": 50,
                },
            },
            {
                "id": "r",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "dangerous_action_executed",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "t", "target": "h"},
            {"id": "e2", "source": "h", "target": "dangerous_action"},
            {"id": "e3", "source": "dangerous_action", "target": "r"},
        ],
    }


@pytest.mark.asyncio
async def test_duplicate_resume_workers_only_one_executes_downstream_side_effect():
    """
    Harsh production case:

    Two resume jobs/workers fire for the same paused workflow run.

    Expected:
        - one worker atomically claims the paused run
        - one worker is rejected as already resuming/not paused
        - dangerous downstream side effect runs exactly once
    """
    _register_test_node()

    store = AtomicClaimingRunStore()

    start_ctx = DummyCtx()
    start_ctx.run_store = store
    start_ctx.extras = {}

    paused = await execute_workflow_dag(
        ctx=start_ctx,
        workflow=_approval_workflow(),
        message="start",
        strict=True,
    )

    assert paused["meta"]["status"] == "paused"

    run_id = paused["meta"]["workflow_run_id"]
    SIDE_EFFECT_CALLS[str(run_id)] = 0

    async def resume_once():
        ctx = DummyCtx()
        ctx.run_store = store
        ctx.extras = {"resume_input": {"approved": True}}

        return await execute_workflow_dag(
            ctx=ctx,
            workflow={},
            message="",
            strict=True,
            resume_workflow_run_id=run_id,
        )

    first, second = await asyncio.gather(resume_once(), resume_once())

    statuses = [first["meta"]["status"], second["meta"]["status"]]
    assert statuses.count("ok") == 1
    assert statuses.count("error") == 1

    error_result = first if first["meta"]["status"] == "error" else second
    assert error_result["meta"]["error"] in {
        "run_already_resuming",
        "run_not_paused",
    }

    assert SIDE_EFFECT_CALLS[str(run_id)] == 1


@pytest.mark.asyncio
async def test_old_resume_job_after_done_does_not_repeat_side_effect():
    """
    Harsh production case:

    A duplicate/late resume job fires after the first resume already completed.

    Expected:
        - second resume is rejected
        - side effect is not repeated
    """
    _register_test_node()

    store = AtomicClaimingRunStore()

    ctx = DummyCtx()
    ctx.run_store = store
    ctx.extras = {}

    paused = await execute_workflow_dag(
        ctx=ctx,
        workflow=_approval_workflow(),
        message="start",
        strict=True,
    )

    run_id = paused["meta"]["workflow_run_id"]
    SIDE_EFFECT_CALLS[str(run_id)] = 0

    ctx.extras = {"resume_input": {"approved": True}}

    first_resume = await execute_workflow_dag(
        ctx=ctx,
        workflow={},
        message="",
        strict=True,
        resume_workflow_run_id=run_id,
    )

    assert first_resume["meta"]["status"] == "ok"
    assert SIDE_EFFECT_CALLS[str(run_id)] == 1

    late_resume = await execute_workflow_dag(
        ctx=ctx,
        workflow={},
        message="",
        strict=True,
        resume_workflow_run_id=run_id,
    )

    assert late_resume["meta"]["status"] == "error"
    assert late_resume["meta"]["error"] == "run_not_paused"
    assert late_resume["meta"]["current_status"] == "done"
    assert SIDE_EFFECT_CALLS[str(run_id)] == 1


@pytest.mark.asyncio
async def test_cancelled_paused_run_cannot_be_resumed_by_old_wait_or_job():
    """
    Harsh production case:

    A workflow pauses. Before the old resume job fires, the run is cancelled.

    Expected:
        - late resume is rejected as run_cancelled
        - downstream side effect does not run
    """
    _register_test_node()

    store = AtomicClaimingRunStore()

    ctx = DummyCtx()
    ctx.run_store = store
    ctx.extras = {}

    paused = await execute_workflow_dag(
        ctx=ctx,
        workflow=_approval_workflow(),
        message="start",
        strict=True,
    )

    assert paused["meta"]["status"] == "paused"

    run_id = paused["meta"]["workflow_run_id"]
    run_uuid = UUID(run_id)
    SIDE_EFFECT_CALLS[str(run_id)] = 0

    await store.update_run(
        run_id=run_uuid,
        status="cancelled",
        state=paused["meta"]["final_state"],
        extra={"reason": "user_cancelled_before_resume_job_fired"},
    )

    ctx.extras = {"resume_input": {"approved": True}}

    late_resume = await execute_workflow_dag(
        ctx=ctx,
        workflow={},
        message="",
        strict=True,
        resume_workflow_run_id=run_id,
    )

    assert late_resume["meta"]["status"] == "error"
    assert late_resume["meta"]["error"] == "run_cancelled"
    assert late_resume["meta"]["current_status"] == "cancelled"
    assert SIDE_EFFECT_CALLS[str(run_id)] == 0
