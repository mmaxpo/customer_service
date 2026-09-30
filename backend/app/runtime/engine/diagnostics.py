from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from app.runtime.engine.router import edge_is_allowed
from app.runtime.utils.graph import build_graph


ROUTER_NODE_TYPES = {"router.rules", "router.llm"}


def _node_type(nodes_by_id: Dict[str, dict], node_id: str) -> str:
    return (nodes_by_id.get(node_id, {}).get("data") or {}).get("nodeType") or ""


def _is_router(nodes_by_id: Dict[str, dict], node_id: str) -> bool:
    return _node_type(nodes_by_id, node_id) in ROUTER_NODE_TYPES


def _incoming_edges(edges: List[dict], nid: str) -> List[dict]:
    return [e for e in edges if e.get("target") == nid and e.get("source")]


def _required_parents_like_executor(
    nodes_by_id: Dict[str, dict],
    edges: List[dict],
    state: Dict[str, Any],
    nid: str,
) -> Tuple[List[str], bool, List[dict], List[dict]]:
    """
    Mirrors the executor logic:
      - all incoming edges count as "has_incoming"
      - only apply condition gating if the edge comes out of a router node
    Returns:
      (required_parent_ids, has_incoming, allowed_edges, blocked_edges)
    """
    inc = _incoming_edges(edges, nid)
    has_incoming = len(inc) > 0

    required: List[str] = []
    allowed_edges: List[dict] = []
    blocked_edges: List[dict] = []

    for e in inc:
        src = e.get("source")
        if not src:
            continue

        if _is_router(nodes_by_id, src):
            if not edge_is_allowed(e, state):
                blocked_edges.append(e)
                continue

        allowed_edges.append(e)
        required.append(src)

    return required, has_incoming, allowed_edges, blocked_edges


def diagnose_deadlock(
    *,
    workflow: dict,
    state: Dict[str, Any],
    started: Set[str],
    finished: Set[str],
) -> Dict[str, Any]:
    """
    Returns a structured explanation of why remaining nodes are blocked.
    Safe to include in API response.
    """
    nodes_by_id, edges, outgoing, incoming = build_graph(workflow)

    remaining = [nid for nid in nodes_by_id.keys() if nid not in finished]
    report: Dict[str, Any] = {
        "remaining": remaining,
        "blocked": {},
        "runnable_now": [],
        "started_not_finished": [],
        "state_route": (state.get("vars") or {}).get("_last_route"),
    }

    for nid in remaining:
        nt = _node_type(nodes_by_id, nid)

        if nid in started and nid not in finished:
            report["started_not_finished"].append(nid)
            report["blocked"][nid] = {
                "node_type": nt,
                "status": "running_or_stuck",
                "reasons": ["node_started_but_not_finished"],
            }
            continue

        required, has_incoming, allowed_edges, blocked_edges = (
            _required_parents_like_executor(nodes_by_id, edges, state, nid)
        )

        # If a node has incoming edges, but currently none are allowed (router gating), it must wait.
        if has_incoming and len(required) == 0:
            reasons = ["no_allowed_incoming_edges"]
            details = {
                "incoming_sources": [
                    e.get("source") for e in _incoming_edges(edges, nid)
                ],
                "blocked_incoming": [
                    {
                        "source": e.get("source"),
                        "condition": e.get("condition"),
                        "reason": "router_condition_blocked",
                    }
                    for e in blocked_edges
                ],
            }

            report["blocked"][nid] = {
                "node_type": nt,
                "status": "blocked",
                "reasons": reasons,
                "details": details,
            }
            continue

        # Otherwise it needs all required parents to be finished.
        missing = [p for p in required if p not in finished]
        if missing:
            report["blocked"][nid] = {
                "node_type": nt,
                "status": "blocked",
                "reasons": ["waiting_for_parents"],
                "details": {
                    "required_parents": required,
                    "missing_parents": missing,
                    "allowed_incoming": [
                        {"source": e.get("source"), "condition": e.get("condition")}
                        for e in allowed_edges
                    ],
                },
            }
            continue

        # If it has no missing parents, it should be runnable.
        report["runnable_now"].append(nid)
        report["blocked"][nid] = {
            "node_type": nt,
            "status": "runnable",
            "reasons": [],
        }

    return report
