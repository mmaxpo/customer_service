from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableSet
from typing import Any

from app.runtime.engine.router import edge_is_allowed


EmitFn = Callable[[dict[str, Any]], Awaitable[None]]


def is_router_node(nodes_by_id: dict[str, dict[str, Any]], node_id: str) -> bool:
    """Return True for nodes whose outgoing edges gate downstream execution."""
    node_type = (nodes_by_id.get(node_id, {}).get("data") or {}).get("nodeType")
    return node_type in {"router.rules", "router.llm", "control.loop"}


def incoming_edges(edges: list[dict[str, Any]], node_id: str) -> list[dict[str, Any]]:
    """Return deterministic incoming edges for a node."""
    node_edges = [
        edge for edge in edges if edge.get("target") == node_id and edge.get("source")
    ]
    node_edges.sort(
        key=lambda edge: (str(edge.get("id") or ""), str(edge.get("source") or ""))
    )
    return node_edges


def parent_node_ids(edges: list[dict[str, Any]], node_id: str) -> list[str]:
    """Return all parent node ids for a node, ignoring router conditions."""
    return [edge["source"] for edge in incoming_edges(edges, node_id)]


def required_parent_node_ids(
    *,
    nodes_by_id: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    state: dict[str, Any],
    node_id: str,
) -> tuple[list[str], bool]:
    """Return parents that must finish before the node can run."""
    required: list[str] = []
    node_edges = incoming_edges(edges, node_id)
    has_incoming = bool(node_edges)

    for edge in node_edges:
        source = edge.get("source")
        if not source:
            continue

        if is_router_node(nodes_by_id, source) and not edge_is_allowed(edge, state):
            continue

        required.append(source)

    return required, has_incoming


def is_node_runnable(
    *,
    nodes_by_id: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    state: dict[str, Any],
    started: set[str],
    finished: set[str],
    node_id: str,
) -> bool:
    """Return True when all required parents have finished and node is unstarted."""
    if node_id in started or node_id in finished:
        return False

    required, has_incoming = required_parent_node_ids(
        nodes_by_id=nodes_by_id,
        edges=edges,
        state=state,
        node_id=node_id,
    )

    if has_incoming and not required:
        return False

    return all(parent in finished for parent in required)


def runnable_node_ids(
    *,
    nodes_by_id: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    state: dict[str, Any],
    started: set[str],
    finished: set[str],
) -> list[str]:
    """Return runnable node ids in deterministic order."""
    return sorted(
        node_id
        for node_id in nodes_by_id.keys()
        if is_node_runnable(
            nodes_by_id=nodes_by_id,
            edges=edges,
            state=state,
            started=started,
            finished=finished,
            node_id=node_id,
        )
    )


async def skip_router_blocked_nodes(
    *,
    nodes_by_id: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    state: dict[str, Any],
    started: set[str],
    finished: MutableSet[str],
    skipped: MutableSet[str],
    emit: EmitFn,
) -> None:
    """Mark nodes skipped when all router parents finished but no route allowed them."""
    for node_id in nodes_by_id.keys():
        if node_id in started or node_id in finished:
            continue

        node_edges = incoming_edges(edges, node_id)
        if not node_edges:
            continue

        if not all(is_router_node(nodes_by_id, edge["source"]) for edge in node_edges):
            continue

        router_parents = {edge["source"] for edge in node_edges}
        if not all(parent in finished for parent in router_parents):
            continue

        if any(edge_is_allowed(edge, state) for edge in node_edges):
            continue

        skipped.add(node_id)
        finished.add(node_id)
        state.setdefault("results", {})[node_id] = None
        await emit(
            {
                "event": "node_skip",
                "node_id": node_id,
                "reason": "router_condition_blocked",
            }
        )


async def skip_downstream_of_skipped_nodes(
    *,
    nodes_by_id: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    state: dict[str, Any],
    started: set[str],
    finished: MutableSet[str],
    skipped: MutableSet[str],
    emit: EmitFn,
) -> None:
    """Cascade skips through nodes whose only possible inputs were skipped."""
    changed = True
    while changed:
        changed = False

        for node_id in nodes_by_id.keys():
            if node_id in started or node_id in finished:
                continue

            parents = parent_node_ids(edges, node_id)
            if not parents:
                continue

            if not all(parent in finished for parent in parents):
                continue

            if len(parents) == 1 and parents[0] in skipped:
                skipped.add(node_id)
                finished.add(node_id)
                state.setdefault("results", {})[node_id] = None
                await emit(
                    {
                        "event": "node_skip",
                        "node_id": node_id,
                        "reason": "parent_skipped",
                    }
                )
                changed = True
                continue

            if len(parents) > 1 and all(parent in skipped for parent in parents):
                skipped.add(node_id)
                finished.add(node_id)
                state.setdefault("results", {})[node_id] = None
                await emit(
                    {
                        "event": "node_skip",
                        "node_id": node_id,
                        "reason": "all_parents_skipped",
                    }
                )
                changed = True
