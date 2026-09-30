from typing import Any
import asyncio

from app.runtime.nodes.executor import call_node, apply_node_result
from app.runtime.engine.router import record_route
from app.runtime.state.run_state import finish_run_state
from app.runtime.engine.policy import get_node_type
from app.runtime.engine.idempotency import (
    build_node_idempotency_key,
    is_side_effect_node,
)
from app.runtime.engine.responses import build_node_error_response
from app.runtime.engine.state_helpers import sync_tracking_sets_to_state_meta
from app.runtime.waits.service import create_runtime_wait


def _output_key_of_node(node_def: dict, fallback: str) -> str:
    data = node_def.get("data") or {}
    node_type = data.get("nodeType")

    if data.get("save_as"):
        return str(data["save_as"])
    if node_type == "trigger.message":
        return "input"
    if node_type == "human.approval":
        return "approval_result"
    if node_type == "join.all":
        return "joined_result"
    if node_type == "agent.custom":
        return "agent_result"

    return fallback


def build_node_execution_data(
    *,
    node_def: dict,
    node_type: str | None,
    node_id: str,
    state_snapshot: dict,
    get_parent_ids,
    nodes_by_id: dict | None = None,
) -> dict:
    """
    Build the per-node data passed into NodeCtx.

    Most nodes receive their normal node.data. The special "join.all" node also
    receives "_join_inputs", which contains outputs from all parent nodes.

    Args:
        node_def: Current node definition.
        node_type: Current node type.
        node_id: Current node id.
        state_snapshot: Stable state snapshot for this execution batch.
        get_parent_ids: Function that returns parent node ids.

    Returns:
        dict: Node data for this execution.

    Example:
        # If parents are ["a", "b"] and their results are "A" and "B":
        data = build_node_execution_data(...)
        assert data["_join_inputs"] == ["A", "B"]
    """
    data = dict(node_def.get("data") or {})

    if is_side_effect_node(node_def):
        data.setdefault("_runtime", {})
        data["_runtime"]["idempotency_key"] = build_node_idempotency_key(
            state=state_snapshot,
            node_id=node_id,
            node_type=node_type,
        )

    if node_type == "join.all":
        parents = get_parent_ids(node_id)
        results = state_snapshot.get("results", {})

        data["_join_inputs"] = [results.get(parent_id) for parent_id in parents]
        data["_join_input_keys"] = [
            _output_key_of_node(
                nodes_by_id.get(parent_id, {}) if nodes_by_id else {},
                parent_id,
            )
            for parent_id in parents
        ]

    return data


async def execute_single_node(
    *,
    ctx,
    node_id: str,
    node_def: dict,
    nodes_by_id: dict,
    state_snapshot: dict,
    get_parent_ids,
) -> tuple[str, dict]:
    """
    Execute one workflow node and return its result with node id.

    This function prepares node execution data, then delegates actual node
    execution to call_node().

    Args:
        ctx: RuntimeContext.
        node_id: Node id to execute.
        node_def: Node definition.
        state_snapshot: Stable state snapshot for this batch.
        get_parent_ids: Function used for join input collection.

    Returns:
        tuple[str, dict]: The node id and raw node result.

    Example:
        node_id, result = await execute_single_node(...)
        assert node_id == "kb_search"
        assert "output" in result
    """
    node_type = get_node_type(node_def)

    node_data = build_node_execution_data(
        node_def=node_def,
        node_type=node_type,
        node_id=node_id,
        state_snapshot=state_snapshot,
        get_parent_ids=get_parent_ids,
        nodes_by_id=nodes_by_id,
    )

    result = await call_node(
        ctx,
        node_def,
        state_snapshot,
        node_data=node_data,
    )

    return node_id, result


async def execute_node_batch(
    *,
    ctx,
    batch: list[str],
    nodes_by_id: dict,
    state_snapshot: dict,
    get_parent_ids,
) -> list[Any]:
    """
    Execute a batch of runnable nodes concurrently.

    The engine decides which nodes are ready. This function runs those nodes
    using asyncio.gather(..., return_exceptions=True), so one node failure does
    not crash the whole gather call.

    Args:
        ctx: RuntimeContext.
        batch: Node ids selected for execution.
        nodes_by_id: Mapping of node_id to node definition.
        state_snapshot: Stable state snapshot shared by the batch.
        get_parent_ids: Function used for join input collection.

    Returns:
        list[Any]: List of either:
            - (node_id, result_dict)
            - Exception

    Example:
        results = await execute_node_batch(
            ctx=ctx,
            batch=["kb", "sentiment"],
            nodes_by_id=nodes_by_id,
            state_snapshot=snapshot,
            get_parent_ids=all_parents,
        )
    """
    return await asyncio.gather(
        *[
            execute_single_node(
                ctx=ctx,
                node_id=node_id,
                node_def=nodes_by_id[node_id],
                nodes_by_id=nodes_by_id,
                state_snapshot=state_snapshot,
                get_parent_ids=get_parent_ids,
            )
            for node_id in batch
        ],
        return_exceptions=True,
    )


def split_batch_results(
    results: list[Any],
) -> tuple[list[tuple[str, Exception]], list[tuple[str, dict]]]:
    """
    Split concurrent batch results into errors and successful node results.

    This keeps engine error handling deterministic by sorting both lists by
    node id.

    Args:
        results: Output from execute_node_batch().

    Returns:
        tuple:
            errors: List of (node_id, exception).
            ok_results: List of (node_id, result_dict).

    Example:
        errors, ok_results = split_batch_results(results)

        if errors:
            bad_node_id, error = errors[0]
    """
    errors: list[tuple[str, Exception]] = []
    ok_results: list[tuple[str, dict]] = []

    for item in results:
        if isinstance(item, Exception):
            errors.append(("__gather__", item))
            continue

        node_id, result = item

        if isinstance(result, Exception):
            errors.append((node_id, result))
        else:
            ok_results.append((node_id, result))

    errors.sort(key=lambda x: x[0])
    ok_results.sort(key=lambda x: x[0])

    return errors, ok_results


async def mark_batch_started(
    *,
    batch: list[str],
    nodes_by_id: dict,
    started: set[str],
    emit,
) -> None:
    """
    Mark every node in the selected batch as started and emit node_start events.

    This happens before execution begins so the frontend can show nodes as active.

    Mutates:
        started

    Emits:
        node_start

    Example:
        await mark_batch_started(
            batch=["kb", "llm"],
            nodes_by_id=nodes_by_id,
            started=started,
            emit=emit,
        )
    """
    for node_id in batch:
        node_def = nodes_by_id[node_id]
        node_type = get_node_type(node_def)
        started.add(node_id)
        await emit(
            {
                "event": "node_start",
                "node_id": node_id,
                "node_type": node_type,
            }
        )


async def handle_batch_error(
    *,
    errors_in_batch: list[tuple[str, Exception]],
    state: dict,
    finished: set[str],
    skipped: set[str],
    emit,
    persist,
    events: list[dict],
) -> dict | None:
    """
    Handle node execution errors from a batch.

    If no errors exist:
        return None.

    If errors exist:
        - choose the first deterministic error
        - emit node_error
        - save error into state["errors"]
        - mark run as failed
        - sync finished/skipped metadata
        - persist failed status
        - return node error response

    Returns:
        dict | None:
            Error response if a node failed, otherwise None.

    Example:
        error_response = await handle_batch_error(...)
        if error_response:
            return error_response
    """
    if not errors_in_batch:
        return None

    bad_node_id, error = errors_in_batch[0]

    await emit(
        {
            "event": "node_error",
            "node_id": bad_node_id,
            "error": repr(error),
        }
    )

    state.setdefault("errors", {})[bad_node_id] = {"error": repr(error)}
    finish_run_state(state, "failed")
    sync_tracking_sets_to_state_meta(
        state,
        finished=finished,
        skipped=skipped,
    )

    await persist(
        "failed",
        extra={
            "failed_node": {"id": bad_node_id},
            "error": repr(error),
        },
    )

    return build_node_error_response(
        state=state,
        failed_node_id=bad_node_id,
        error=error,
        events=events,
    )


async def handle_loop_continue(
    *,
    node_id: str,
    node_result: dict,
    state: dict,
    started: set[str],
    finished: set[str],
    skipped: set[str],
    emit,
) -> None:
    """
    Reset loop-controlled nodes when a control.loop node routes to "continue".

    This allows selected nodes to run again in the next scheduler iteration.
    """
    reset_ids = node_result.get("loop_reset") or []
    if not isinstance(reset_ids, list):
        reset_ids = []

    reset_all = list(dict.fromkeys(reset_ids + [node_id]))

    state.setdefault("vars", {})
    state["vars"].pop("route_key", None)
    state["vars"].pop("_last_route", None)

    for reset_id in reset_all:
        started.discard(reset_id)
        finished.discard(reset_id)
        skipped.discard(reset_id)

        if state.get("results") and reset_id in state["results"]:
            del state["results"][reset_id]

        node_meta = state.get("meta", {}).get("node_meta_by_id", {})
        if node_meta and reset_id in node_meta:
            del node_meta[reset_id]

    await emit(
        {
            "event": "loop_continue",
            "node_id": node_id,
            "reset": reset_all,
        }
    )


async def apply_successful_batch_results(
    *,
    ctx,
    ok_results: list[tuple[str, dict]],
    nodes_by_id: dict,
    state: dict,
    started: set[str],
    finished: set[str],
    skipped: set[str],
    emit,
) -> tuple[dict, tuple[str, dict] | None]:
    """
    Apply successful node results to RunState.

    This function:
        - merges each node result into state
        - records routing decisions
        - emits node_end
        - handles control.loop rewind
        - detects paused node result
        - marks completed nodes as finished

    Returns:
        tuple:
            updated state
            paused_hit, if a node paused the workflow
    """
    paused_hit: tuple[str, dict] | None = None

    for node_id, node_result in ok_results:
        node_def = nodes_by_id[node_id]
        node_type = get_node_type(node_def)

        state = apply_node_result(state, node_def, node_result)
        record_route(state, node_result.get("route"))

        node_meta = node_result.get("meta") or {}

        await emit(
            {
                "event": "node_end",
                "node_id": node_id,
                "node_type": node_type,
                "output": node_result.get("output"),
                "meta": node_meta,
            }
        )

        is_loop_continue = (
            node_type == "control.loop" and node_result.get("route") == "continue"
        )

        if is_loop_continue:
            await handle_loop_continue(
                node_id=node_id,
                node_result=node_result,
                state=state,
                started=started,
                finished=finished,
                skipped=skipped,
                emit=emit,
            )

        if node_result.get("status") == "paused" and paused_hit is None:
            runtime_wait = node_result.get("wait")

            if runtime_wait is not None and getattr(ctx, "db", None) is not None:
                workflow_run_id = (
                    state.get("run_id")
                    or state.get("workflow_run_id")
                    or state.get("id")
                    or state.get("meta", {}).get("workflow_run_id")
                    or state.get("meta", {}).get("run_id")
                    or getattr(ctx, "thread_id", None)
                )

                created_wait = await create_runtime_wait(
                    ctx=ctx,
                    workflow_run_id=str(workflow_run_id),
                    node_id=node_id,
                    wait=runtime_wait,
                )

                state.setdefault("meta", {})

                existing_interrupt = (
                    state["meta"].get("interrupt") or node_result.get("interrupt") or {}
                )

                if not isinstance(existing_interrupt, dict):
                    existing_interrupt = {}

                state["meta"]["interrupt"] = {
                    **existing_interrupt,
                    "kind": existing_interrupt.get("kind") or created_wait.wait_type,
                    "type": "workflow_wait",
                    "workflow_wait_id": str(created_wait.id),
                    "wait_id": str(created_wait.id),
                    "wait_type": created_wait.wait_type,
                    "node_id": node_id,
                    "payload": created_wait.payload,
                }

                node_result["interrupt"] = state["meta"]["interrupt"]

                node_result.setdefault("meta", {})
                node_result["meta"]["workflow_wait_id"] = str(created_wait.id)
                node_result["meta"]["wait_type"] = created_wait.wait_type

            paused_hit = (node_id, node_result)

        should_finish = node_result.get("status") != "paused"
        if is_loop_continue:
            should_finish = False

        if should_finish:
            finished.add(node_id)

    return state, paused_hit
