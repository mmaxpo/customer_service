from __future__ import annotations

from typing import Any, Dict, List, Optional
import time
import uuid

from app.runtime.utils.graph import build_graph, find_trigger_node_id
from app.runtime.state.run_state import new_run_state, finish_run_state
from app.runtime.engine.validator import validate_workflow
from app.runtime.engine.policy import ExecutionPolicy, batch_contains_response_node
from app.workflow_operations.snapshots.service import WorkflowSnapshotService
from app.runtime.engine.responses import build_error_response
from app.runtime.engine.lifecycle import initialize_run_lifecycle
from app.runtime.engine.completion import (
    complete_workflow_run,
    pause_workflow_run,
)
from app.runtime.engine.state_helpers import (
    get_persistence_adapters,
    normalize_resumed_state,
    update_run_attempt,
    inject_resume_payload,
    restore_tracking_sets,
    create_state_snapshot,
    sync_tracking_sets_to_state_meta,
    check_cancel_requested,
    handle_no_ready_nodes,
)
from app.runtime.engine.replay_safety import skip_replay_blocked_nodes
from app.runtime.engine.scheduler import (
    parent_node_ids,
    runnable_node_ids,
    skip_downstream_of_skipped_nodes,
    skip_router_blocked_nodes,
)
from app.runtime.engine.execution import (
    execute_node_batch,
    split_batch_results,
    mark_batch_started,
    handle_batch_error,
    apply_successful_batch_results,
)


class WorkflowExecutionError(Exception):
    """
    Runtime-level exception for workflow execution failures.

    This is reserved for engine-specific errors that are not normal node failures.

    Example:
        raise WorkflowExecutionError("Workflow cannot continue")
    """


async def execute_workflow_dag(
    *,
    ctx,
    workflow: dict,
    message: str,
    max_steps: int = 500,
    strict: bool = True,
    resume_workflow_run_id: Optional[str] = None,
    max_concurrency: int = 8,
    replay_state: Optional[dict] = None,
    replay_parent_workflow_run_id: Optional[str] = None,
) -> dict:
    """
    Execute a workflow DAG from React Flow JSON.

    This is the main runtime entry point called by /workflows_route/run.

    High-level flow:
        1. Get persistence adapters.
        2. Create ExecutionPolicy.
        3. Create new state or resume paused state.
        4. Validate workflow.
        5. Build graph maps.
        6. Find trigger.message node.
        7. Create run record.
        8. Restore tracking sets.
        9. Emit run_start or run_resume.
        10. Enter scheduler loop.
        11. Find runnable nodes.
        12. Select execution batch.
        13. Execute nodes concurrently.
        14. Apply node results.
        15. Handle routing, skipping, pause, loop, errors.
        16. Finish run and return final response.

    Args:
        ctx: RuntimeContext created by the FastAPI router.
        workflow: React Flow workflow JSON with nodes and edges.
        message: Initial user/customer message.
        max_steps: Safety limit for scheduler loop iterations.
        strict: If True, validate workflow before running.
        resume_workflow_run_id: Existing paused run id to resume.
        max_concurrency: Maximum nodes executed in one batch.

    Returns:
        dict:
            {
                "answer": final_output_or_none,
                "meta": {
                    "status": "ok" | "error" | "paused" | "deadlock" | "cancelled",
                    ...
                }
            }

    Example:
        result = await execute_workflow_dag(
            ctx=ctx,
            workflow={
                "nodes": [
                    {"id": "t", "data": {"nodeType": "trigger.message"}},
                    {"id": "r", "data": {"nodeType": "response"}},
                ],
                "edges": [
                    {"source": "t", "target": "r"},
                ],
            },
            message="Where is my order?",
        )

        assert result["meta"]["status"] == "ok"
    """

    run_store, event_sink = get_persistence_adapters(ctx)

    policy = ExecutionPolicy(
        max_steps=max_steps,
        max_concurrency=max_concurrency,
    )
    # ✅ resume requires persistence
    if resume_workflow_run_id and not run_store:
        return build_error_response(
            error="resume_requires_run_store",
            workflow_run_id=resume_workflow_run_id,
        )

    if replay_state is not None:
        state = normalize_resumed_state(replay_state)
        original_workflow_run_id = state.get("workflow_run_id")

        state["workflow_run_id"] = uuid.uuid4()
        state.setdefault("meta", {})
        state["meta"]["replay"] = {
            "enabled": True,
            "parent_workflow_run_id": str(
                replay_parent_workflow_run_id or original_workflow_run_id or ""
            ),
        }
        state["meta"]["status"] = "running"

    elif resume_workflow_run_id and run_store:
        rid = uuid.UUID(resume_workflow_run_id)

        if hasattr(run_store, "claim_run_for_resume"):
            saved = await run_store.claim_run_for_resume(run_id=rid)

            if not saved:
                current = await run_store.load_run(run_id=rid)

                if not current:
                    return build_error_response(
                        error="run_not_found",
                        workflow_run_id=resume_workflow_run_id,
                    )

                current_status = current.get("status")

                if current_status == "cancelled":
                    return build_error_response(
                        error="run_cancelled",
                        workflow_run_id=resume_workflow_run_id,
                        current_status=current_status,
                    )

                if current_status == "running":
                    return build_error_response(
                        error="run_already_resuming",
                        workflow_run_id=resume_workflow_run_id,
                        current_status=current_status,
                    )

                return build_error_response(
                    error="run_not_paused",
                    workflow_run_id=resume_workflow_run_id,
                    current_status=current_status,
                )
        else:
            saved = await run_store.load_run(run_id=rid)

            if not saved:
                return build_error_response(
                    error="run_not_found",
                    workflow_run_id=resume_workflow_run_id,
                )

            if saved.get("status") == "cancelled":
                return build_error_response(
                    error="run_cancelled",
                    workflow_run_id=resume_workflow_run_id,
                    current_status=saved.get("status"),
                )

            if saved.get("status") != "paused":
                return build_error_response(
                    error="run_not_paused",
                    workflow_run_id=resume_workflow_run_id,
                    current_status=saved.get("status"),
                )

        workflow = saved["workflow"]
        state = normalize_resumed_state(saved["state"])
    else:
        state = new_run_state(message)

    is_resume = bool(resume_workflow_run_id)
    attempt = update_run_attempt(state, is_resume=is_resume)

    # ---- validation ----
    if strict:
        verrs = validate_workflow(workflow)

        if verrs:
            return build_error_response(
                error="invalid_workflow",
                validation_errors=[e.__dict__ for e in verrs],
            )

    inject_resume_payload(state, ctx)

    nodes_by_id, edges, _outgoing, _incoming = build_graph(workflow)

    trigger_id = find_trigger_node_id(nodes_by_id)
    if not trigger_id:
        finish_run_state(state, "failed")
        return build_error_response(
            error="missing_trigger",
            run_id=str(state.get("workflow_run_id")),
            answer=state.get("last"),
            nodes=list(nodes_by_id.keys()),
        )

    # execution tracking sets: These are the runtime brain.

    started, finished, skipped = restore_tracking_sets(state)

    events: List[dict] = state["meta"]["events"]

    async def emit(ev: Dict[str, Any]) -> None:
        ev.setdefault("run_attempt", attempt)
        events.append(ev)
        if event_sink:
            await event_sink.emit(state["workflow_run_id"], ev)

    async def persist(status: str, extra: Optional[Dict[str, Any]] = None) -> None:
        if run_store:
            await run_store.update_run(
                run_id=state["workflow_run_id"], status=status, state=state, extra=extra
            )

    async def capture_snapshot(
        snapshot_type: str,
        *,
        node_id: str | None = None,
        node_type: str | None = None,
        event: dict | None = None,
    ) -> None:
        if not getattr(ctx, "db", None):
            return

        await WorkflowSnapshotService(ctx.db).capture(
            workflow_run_id=state["workflow_run_id"],
            user_id=getattr(ctx, "user_id", None),
            snapshot_type=snapshot_type,
            node_id=node_id,
            node_type=node_type,
            state=state,
            event=event or {},
        )

    await initialize_run_lifecycle(
        run_store=run_store,
        ctx=ctx,
        workflow=workflow,
        state=state,
        is_resume=is_resume,
        emit=emit,
        capture_snapshot=capture_snapshot,
    )

    steps = 0
    t0 = time.time()

    while policy.can_continue(steps=steps):
        steps += 1

        # ✅ cancellation check (best-effort)
        cancel_response = await check_cancel_requested(
            run_store=run_store,
            state=state,
            emit=emit,
            persist=persist,
            events=events,
        )
        if cancel_response:
            return cancel_response

        await skip_router_blocked_nodes(
            nodes_by_id=nodes_by_id,
            edges=edges,
            state=state,
            started=started,
            finished=finished,
            skipped=skipped,
            emit=emit,
        )
        await skip_downstream_of_skipped_nodes(
            nodes_by_id=nodes_by_id,
            edges=edges,
            state=state,
            started=started,
            finished=finished,
            skipped=skipped,
            emit=emit,
        )

        ready = runnable_node_ids(
            nodes_by_id=nodes_by_id,
            edges=edges,
            state=state,
            started=started,
            finished=finished,
        )

        replay_skipped = await skip_replay_blocked_nodes(
            ready=ready,
            nodes_by_id=nodes_by_id,
            state=state,
            started=started,
            finished=finished,
            skipped=skipped,
            emit=emit,
        )

        if replay_skipped:
            await skip_downstream_of_skipped_nodes(
                nodes_by_id=nodes_by_id,
                edges=edges,
                state=state,
                started=started,
                finished=finished,
                skipped=skipped,
                emit=emit,
            )
            sync_tracking_sets_to_state_meta(
                state,
                finished=finished,
                skipped=skipped,
            )
            ready = runnable_node_ids(
                nodes_by_id=nodes_by_id,
                edges=edges,
                state=state,
                started=started,
                finished=finished,
            )

        if not ready:
            no_ready_response = await handle_no_ready_nodes(
                state=state,
                nodes_by_id=nodes_by_id,
                finished=finished,
                persist=persist,
                events=events,
            )
            if no_ready_response:
                return no_ready_response
            break

        batch = policy.select_batch(
            ready=ready,
            nodes_by_id=nodes_by_id,
        )

        await mark_batch_started(
            batch=batch,
            nodes_by_id=nodes_by_id,
            started=started,
            emit=emit,
        )

        state_snapshot = create_state_snapshot(state)

        results = await execute_node_batch(
            ctx=ctx,
            batch=batch,
            nodes_by_id=nodes_by_id,
            state_snapshot=state_snapshot,
            get_parent_ids=lambda node_id: parent_node_ids(edges, node_id),
        )

        errors_in_batch, ok_results = split_batch_results(results)

        batch_error_response = await handle_batch_error(
            errors_in_batch=errors_in_batch,
            state=state,
            finished=finished,
            skipped=skipped,
            emit=emit,
            persist=persist,
            events=events,
        )
        if batch_error_response:
            return batch_error_response

        state, paused_hit = await apply_successful_batch_results(
            ctx=ctx,
            ok_results=ok_results,
            nodes_by_id=nodes_by_id,
            state=state,
            started=started,
            finished=finished,
            skipped=skipped,
            emit=emit,
        )

        for _node_id, _node_result in ok_results:
            _node_def = nodes_by_id[_node_id]
            _node_type = (_node_def.get("data") or {}).get("nodeType")
            await capture_snapshot(
                "node_end",
                node_id=_node_id,
                node_type=_node_type,
                event={
                    "node_id": _node_id,
                    "node_type": _node_type,
                    "output": _node_result.get("output"),
                    "meta": _node_result.get("meta") or {},
                    "status": _node_result.get("status"),
                },
            )
        sync_tracking_sets_to_state_meta(
            state,
            finished=finished,
            skipped=skipped,
        )

        if paused_hit:
            _node_id, node_result = paused_hit
            return await pause_workflow_run(
                state=state,
                node_result=node_result,
                emit=emit,
                persist=lambda status, extra=None: persist(status, extra=extra),
                events=events,
            )

        await skip_router_blocked_nodes(
            nodes_by_id=nodes_by_id,
            edges=edges,
            state=state,
            started=started,
            finished=finished,
            skipped=skipped,
            emit=emit,
        )
        await skip_downstream_of_skipped_nodes(
            nodes_by_id=nodes_by_id,
            edges=edges,
            state=state,
            started=started,
            finished=finished,
            skipped=skipped,
            emit=emit,
        )
        sync_tracking_sets_to_state_meta(
            state,
            finished=finished,
            skipped=skipped,
        )

        if batch_contains_response_node(
            batch=batch,
            nodes_by_id=nodes_by_id,
        ):
            break

    dt = time.time() - t0

    return await complete_workflow_run(
        state=state,
        steps=steps,
        elapsed_sec=dt,
        emit=emit,
        persist=lambda status, extra=None: persist(status, extra=extra),
        capture_snapshot=capture_snapshot,
        events=events,
    )
