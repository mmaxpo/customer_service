from app.runtime.state.run_state import finish_run_state
from app.runtime.engine.responses import (
    build_cancelled_response,
    build_deadlock_response,
)


def get_persistence_adapters(ctx):
    """
    Read optional persistence adapters from RuntimeContext.

    The workflow engine can run with or without persistence. When persistence
    exists, run state and events are saved through these adapters.

    Returns:
        tuple[RunStore | None, EventSink | None]:
            run_store saves workflow state.
            event_sink saves runtime events.

    Example:
        run_store, event_sink = get_persistence_adapters(ctx)

        if run_store:
            await run_store.update_run(...)
    """
    return getattr(ctx, "run_store", None), getattr(ctx, "event_sink", None)


def normalize_resumed_state(state: dict) -> dict:
    """
    Ensure a loaded paused RunState has all required runtime keys.

    When a workflow resumes from the database, older saved states may miss keys.
    This function guarantees the engine can safely continue execution.

    Mutates:
        state["meta"]["events"]
        state["meta"]["node_meta_by_id"]
        state["meta"]["interrupt"]
        state["results"]
        state["errors"]
        state["vars"]
        state["memory"]
        state["last"]
        state["status"]

    Returns:
        dict: The normalized state.

    Example:
        state = normalize_resumed_state(saved["state"])
        assert state["status"] == "running"
        assert "results" in state
    """
    state.setdefault("meta", {}).setdefault("events", [])
    state.setdefault("meta", {}).setdefault("node_meta_by_id", {})
    state.setdefault("meta", {}).setdefault("interrupt", None)
    state.setdefault("results", {})
    state.setdefault("errors", {})
    state.setdefault("vars", {})
    state.setdefault("memory", {})
    state.setdefault("last", state.get("last"))
    state["status"] = "running"
    return state


def update_run_attempt(state: dict, *, is_resume: bool) -> int:
    """
    Update and return the current run attempt number.

    A new workflow starts at attempt 1. Every resume increments the attempt,
    which helps distinguish events emitted before and after human approval.

    Args:
        state: Current workflow run state.
        is_resume: True when continuing a paused run.

    Returns:
        int: Current attempt number.

    Example:
        attempt = update_run_attempt(state, is_resume=True)
        # state["meta"]["run_attempt"] is now incremented
    """
    meta = state.setdefault("meta", {})
    attempt = int(meta.get("run_attempt") or 1)
    if is_resume:
        attempt += 1
    meta["run_attempt"] = attempt
    return attempt


def inject_resume_payload(state: dict, ctx) -> None:
    """
    Store resume input into state variables.

    When a paused workflow resumes, the frontend may send extra input such as
    human approval result. This function places that value at:

        state["vars"]["resume_input"]

    Args:
        state: Current workflow run state.
        ctx: RuntimeContext, optionally containing ctx.extras["resume_input"].

    Example:
        ctx.extras = {"resume_input": {"approved": True}}
        inject_resume_payload(state, ctx)

        assert state["vars"]["resume_input"] == {"approved": True}
    """
    resume_payload = None
    if getattr(ctx, "extras", None):
        resume_payload = ctx.extras.get("resume_input")

    if resume_payload is not None:
        state.setdefault("vars", {})
        state["vars"]["resume_input"] = resume_payload


def restore_tracking_sets(state: dict) -> tuple[set[str], set[str], set[str]]:
    """
    Restore runtime tracking sets from RunState metadata.

    The engine tracks which nodes are started, finished, or skipped.
    On resume, started nodes are never restored because in-flight work should
    not be considered active after a pause.

    Returns:
        tuple:
            started: Always empty on restore.
            finished: Node ids already completed.
            skipped: Node ids skipped by routing or parent skip logic.

    Example:
        state["meta"]["finished_node_ids"] = ["trigger", "kb"]
        started, finished, skipped = restore_tracking_sets(state)

        assert started == set()
        assert finished == {"trigger", "kb"}
    """
    meta = state.setdefault("meta", {})
    started = set()
    finished = set(meta.get("finished_node_ids", []) or [])
    skipped = set(meta.get("skipped_node_ids", []) or [])
    return started, finished, skipped


def create_state_snapshot(state: dict) -> dict:
    """
    Create a shallow isolated snapshot for parallel node execution.

    Parallel nodes should read the same stable state and should not mutate the
    live shared state directly. The engine later applies node results in a
    deterministic order.

    Copies:
        vars
        results
        memory
        meta
        errors
        meta["node_meta_by_id"]

    Returns:
        dict: Snapshot state passed to node execution.

    Example:
        snapshot = create_state_snapshot(state)
        snapshot["vars"]["x"] = 10

        # state["vars"] is not directly modified by that change.
    """
    snapshot = {
        **state,
        "vars": dict(state.get("vars", {}) or {}),
        "results": dict(state.get("results", {}) or {}),
        "memory": dict(state.get("memory", {}) or {}),
        "meta": dict(state.get("meta", {}) or {}),
        "errors": dict(state.get("errors", {}) or {}),
    }

    if "node_meta_by_id" in snapshot["meta"]:
        snapshot["meta"]["node_meta_by_id"] = dict(
            snapshot["meta"]["node_meta_by_id"] or {}
        )

    return snapshot


def sync_tracking_sets_to_state_meta(
    state: dict,
    *,
    finished: set[str],
    skipped: set[str],
) -> None:
    """
    Persist runtime tracking sets into state metadata.

    This allows pause/resume and frontend debugging to know which nodes were
    completed or skipped.

    Writes:
        state["meta"]["finished_node_ids"]
        state["meta"]["skipped_node_ids"]

    Example:
        finished = {"trigger", "kb"}
        skipped = {"refund_path"}

        sync_tracking_sets_to_state_meta(
            state,
            finished=finished,
            skipped=skipped,
        )
    """
    state.setdefault("meta", {})
    state["meta"]["finished_node_ids"] = sorted(list(finished))
    state["meta"]["skipped_node_ids"] = sorted(list(skipped))


async def check_cancel_requested(
    *,
    run_store,
    state: dict,
    emit,
    persist,
    events: list[dict],
) -> dict | None:
    """
    Check whether the current run was cancelled.

    Cancellation is best-effort:
        - If run_store is missing, do nothing.
        - If run_store has no is_cancel_requested method, do nothing.
        - If the check itself fails, do nothing.

    When cancellation is requested:
        - mark state as cancelled
        - emit run_cancelled
        - persist cancelled status
        - return cancelled response

    Returns:
        dict | None:
            Cancelled response if cancelled, otherwise None.

    Example:
        cancel_response = await check_cancel_requested(...)
        if cancel_response:
            return cancel_response
    """
    if not run_store or not hasattr(run_store, "is_cancel_requested"):
        return None

    try:
        is_cancelled = await run_store.is_cancel_requested(
            run_id=state["workflow_run_id"]
        )
    except Exception:
        return None

    if not is_cancelled:
        return None

    finish_run_state(state, "cancelled")
    await emit(
        {"event": "run_cancelled", "workflow_run_id": str(state["workflow_run_id"])}
    )
    await persist("cancelled")

    return build_cancelled_response(state=state, events=events)


async def handle_no_ready_nodes(
    *,
    state: dict,
    nodes_by_id: dict,
    finished: set[str],
    persist,
    events: list[dict],
) -> dict | None:
    """
    Handle the case where no nodes are runnable.

    If all nodes are finished:
        return None, meaning the workflow can exit normally.

    If some nodes are unfinished:
        mark the workflow as failed due to deadlock and return a deadlock response.

    A deadlock means:
        - no runnable nodes
        - unfinished nodes still exist

    Example:
        no_ready_response = await handle_no_ready_nodes(...)
        if no_ready_response:
            return no_ready_response
        break
    """
    if len(finished) >= len(nodes_by_id):
        return None

    remaining = [node_id for node_id in nodes_by_id.keys() if node_id not in finished]

    finish_run_state(state, "failed")
    await persist("failed", extra={"reason": "deadlock", "remaining": remaining})

    return build_deadlock_response(
        state=state,
        remaining=remaining,
        finished=finished,
        events=events,
    )
