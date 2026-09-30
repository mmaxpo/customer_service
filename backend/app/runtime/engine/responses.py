from typing import Any


def build_error_response(
    *,
    error: str,
    workflow_run_id: str | None = None,
    answer: Any = None,
    **meta_extra,
) -> dict:
    """
    Build a standard error response for workflow execution.

    Used for validation errors, missing trigger, resume errors, and other
    non-node-specific failures.

    Args:
        error: Machine-readable error code.
        workflow_run_id : Optional workflow run id.
        answer: Optional answer payload.
        **meta_extra: Additional metadata.

    Returns:
        dict: API response shape.

    Example:
        return build_error_response(
            error="missing_trigger",
            workflow_run_id=state["workflow_run_id"],
            nodes=list(nodes_by_id.keys()),
        )
    """
    meta = {
        "status": "error",
        "error": error,
    }

    if workflow_run_id is not None:
        meta["workflow_run_id"] = str(workflow_run_id)

    meta.update(meta_extra)

    return {
        "answer": answer,
        "meta": meta,
    }


def build_cancelled_response(
    *,
    state: dict,
    events: list[dict],
) -> dict:
    """
    Build response for a cancelled workflow run.

    A workflow is cancelled when the RunStore says cancellation was requested.

    Returns:
        dict: API response with status "cancelled".

    Example:
        return build_cancelled_response(
            state=state,
            events=events,
        )
    """
    return {
        "answer": state.get("last"),
        "meta": {
            "status": "cancelled",
            "workflow_run_id": str(state.get("workflow_run_id")),
            "events": events,
            "final_state": state,
        },
    }


def build_deadlock_response(
    *,
    state: dict,
    remaining: list[str],
    finished: set[str],
    events: list[dict],
) -> dict:
    """
    Build response for a deadlocked workflow.

    A deadlock means:
        - There are unfinished nodes.
        - No node is currently runnable.

    This usually means routing, graph structure, or parent dependencies blocked
    progress.

    Args:
        remaining: Node ids not finished.
        finished: Node ids already finished.

    Returns:
        dict: API response with status "deadlock".

    Example:
        return build_deadlock_response(
            state=state,
            remaining=["response"],
            finished={"trigger"},
            events=events,
        )
    """
    return {
        "answer": state.get("last"),
        "meta": {
            "status": "deadlock",
            "workflow_run_id": str(state.get("workflow_run_id")),
            "remaining": remaining,
            "finished": list(finished),
            "outputs_by_node_id": state.get("results", {}),
            "node_meta_by_id": state.get("meta", {}).get("node_meta_by_id", {}),
            "events": events,
            "final_state": state,
        },
    }


def build_node_error_response(
    *,
    state: dict,
    failed_node_id: str,
    error: Exception,
    events: list[dict],
) -> dict:
    """
    Build response when one node fails during execution.

    This is used after:
        - node_error event is emitted
        - state["errors"] is updated
        - run state is marked failed
        - run is persisted as failed

    Args:
        failed_node_id: Node id that failed.
        error: Exception raised by that node.
        events: Runtime events emitted so far.

    Returns:
        dict: API response with status "error".

    Example:
        return build_node_error_response(
            state=state,
            failed_node_id="kb_search",
            error=err,
            events=events,
        )
    """
    return {
        "answer": state.get("last"),
        "meta": {
            "status": "error",
            "workflow_run_id": str(state.get("workflow_run_id")),
            "error": repr(error),
            "failed_node": {"id": failed_node_id},
            "events": events,
            "final_state": state,
        },
    }


def build_paused_response(
    *,
    state: dict,
    interrupt: dict,
    events: list[dict],
) -> dict:
    """
    Build response for a paused workflow run.

    A workflow pauses when a node returns:
        {"status": "paused", "interrupt": {...}}

    Common use cases:
        - human approval
        - waiting for manual review
        - waiting for external input

    Returns:
        dict: API response with status "paused".

    Example:
        return build_paused_response(
            state=state,
            interrupt={"reason": "needs_human_approval"},
            events=events,
        )
    """
    return {
        "answer": state.get("last"),
        "meta": {
            "status": "paused",
            "workflow_run_id": str(state.get("workflow_run_id")),
            "interrupt": interrupt,
            "outputs_by_node_id": state.get("results", {}),
            "node_meta_by_id": state.get("meta", {}).get("node_meta_by_id", {}),
            "events": events,
            "final_state": state,
        },
    }


def build_success_response(
    *,
    state: dict,
    steps: int,
    elapsed_sec: float,
    events: list[dict],
) -> dict:
    """
    Build response for a successfully completed workflow run.

    The final user-visible answer is stored in:
        state["last"]

    The frontend also receives detailed metadata for debugging and UI replay.

    Returns:
        dict: API response with status "ok".

    Example:
        return build_success_response(
            state=state,
            steps=4,
            elapsed_sec=0.35,
            events=events,
        )
    """
    return {
        "answer": state.get("last"),
        "meta": {
            "status": "ok",
            "workflow_run_id": str(state.get("workflow_run_id")),
            "steps": steps,
            "elapsed_sec": elapsed_sec,
            "outputs_by_node_id": state.get("results", {}),
            "node_meta_by_id": state.get("meta", {}).get("node_meta_by_id", {}),
            "events": events,
            "final_state": state,
        },
    }
