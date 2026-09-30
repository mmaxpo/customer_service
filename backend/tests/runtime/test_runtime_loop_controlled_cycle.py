from __future__ import annotations

import pytest
from app.runtime.engine.executor import execute_workflow_dag
from app.runtime.engine.validator import validate_workflow


def _codes(errs) -> set[str]:
    return {getattr(e, "code", "") for e in (errs or [])}


def test_validator_allows_cycle_if_loop_in_cycle():
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
            {"id": "r", "data": {"nodeType": "response"}},
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
                "target": "r",
                "when": {"eq": ["vars.route_key", "stop"]},
            },
        ],
    }
    errs = validate_workflow(wf)
    assert "cycle_detected" not in _codes(errs), errs


@pytest.mark.asyncio
async def test_control_loop_runs_and_stops(ctx):
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
            {"id": "r", "data": {"nodeType": "response"}},
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
                "target": "r",
                "when": {"eq": ["vars.route_key", "stop"]},
            },
        ],
    }

    out = await execute_workflow_dag(ctx=ctx, workflow=wf, message="")
    assert out["meta"]["status"] == "ok"

    # loop_count should end at 3
    final_state = out["meta"]["final_state"]
    assert final_state["vars"]["loop_count"] == 3

    # should have emitted loop_continue events (2 times: continue, continue, then stop)
    events = out["meta"].get("events") or []
    assert sum(1 for e in events if e.get("event") == "loop_continue") == 2
