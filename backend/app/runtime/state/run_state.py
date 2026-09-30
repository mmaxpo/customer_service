from __future__ import annotations

from typing import Any, Dict, Optional
import uuid
import time


def new_run_state(message: Optional[str]) -> Dict[str, Any]:
    """
    Create a new workflow RunState.

    This initializes all required runtime fields used by the execution engine.
    It guarantees a consistent state shape across all workflows_route.

    State structure:
        {
            "workflow_run_id": UUID,
            "status": "running",
            "vars": {},        # shared variables across nodes
            "memory": {},      # long-lived memory (future use)
            "results": {},     # outputs by node_id
            "errors": {},      # node execution errors
            "meta": {
                "events": [],              # emitted runtime events
                "node_meta_by_id": {},    # per-node metadata
                "created_at_ts": float,
                "updated_at_ts": float,
            },
            "last": Any        # last node output
        }

    Special behavior:
        If message is provided:
            - stored in state["vars"]["input"]
            - also set as state["last"]

    Args:
        message: Initial user/customer input.

    Returns:
        dict: Initialized RunState.

    Example:
        state = new_run_state("Where is my order?")

        assert state["status"] == "running"
        assert state["vars"]["input"] == "Where is my order?"
        assert state["last"] == "Where is my order?"
    """
    run_id = uuid.uuid4()
    # TODO
    # change to --> "workflow_run_id": str(uuid.uuid4())
    # Correct production rule
    # Use this pattern:
    # Internal runtime/store: UUID object
    # API response: str(UUID)
    # JSON persistence layer: serialize to string only at boundary
    now = time.time()

    state: Dict[str, Any] = {
        "workflow_run_id": run_id,
        "status": "running",
        "vars": {},
        "memory": {},
        "results": {},
        "errors": {},
        "meta": {
            "events": [],
            "node_meta_by_id": {},
            "created_at_ts": now,
            "updated_at_ts": now,
        },
        "last": None,
    }

    if message is not None:
        state["vars"]["input"] = message
        state["last"] = message

    return state


def finish_run_state(state: Dict[str, Any], status: str) -> None:
    """
    Mark the workflow run as finished and update timestamp.

    This function is called when a workflow:
        - completes successfully ("done")
        - fails ("failed")
        - is paused ("paused")
        - is cancelled ("cancelled")

    It updates:
        state["status"]
        state["meta"]["updated_at_ts"]

    Args:
        state: Current RunState.
        status: Final status string.

    Example:
        finish_run_state(state, "done")

        assert state["status"] == "done"
        assert "updated_at_ts" in state["meta"]
    """
    state["status"] = status
    state.setdefault("meta", {})
    state["meta"]["updated_at_ts"] = time.time()
