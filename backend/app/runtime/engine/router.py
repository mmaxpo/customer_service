from __future__ import annotations

from typing import Any, Dict, List, Optional

ROUTE_STATE_KEY = "_last_route"  # stored in state["vars"][ROUTE_STATE_KEY]


def record_route(state: Dict[str, Any], route: Optional[str]) -> None:
    """

    Store the last routing decision in RunState variables.

    Router-like nodes can return:

        {"route": "refund"}

    The executor records that route at:

        state["vars"]["_last_route"]

    Args:

        state: Current workflow RunState.

        route: Route key returned by a router node.

    Example:

        record_route(state, "refund")

        assert state["vars"]["_last_route"] == "refund"

    """
    if not route:
        return
    state.setdefault("vars", {})
    state["vars"][ROUTE_STATE_KEY] = route


def get_last_route(state: Dict[str, Any]) -> Optional[str]:
    """
    Return the last route selected by a router/control node.

    Reads:
        state["vars"]["_last_route"]

    Args:
        state: Current workflow RunState.

    Returns:
        str | None: Last route key.

    Example:
        state = {"vars": {"_last_route": "shipping"}}

        assert get_last_route(state) == "shipping"
    """
    return (state.get("vars") or {}).get(ROUTE_STATE_KEY)


def outgoing_edges(edges: List[dict], source_id: str) -> List[dict]:
    """
    Return all edges that start from a source node.

    Args:
        edges: Workflow edge list.
        source_id: Source node id.

    Returns:
        list[dict]: Edges where edge["source"] == source_id.

    Example:
        edges = [
            {"source": "router", "target": "refund"},
            {"source": "router", "target": "shipping"},
        ]

        assert len(outgoing_edges(edges, "router")) == 2
    """
    return [e for e in edges if e.get("source") == source_id]


# -----------------------------
# Safe condition evaluation
# -----------------------------
When = Dict[str, Any]


def _get_ref_value(ref: Any, state: Dict[str, Any]) -> Any:
    """
    Resolve a safe condition reference against RunState.

    Supported references:
        "vars.foo"       -> state["vars"]["foo"]
        "last"           -> state["last"]
        "route"          -> latest recorded route
        "results.nodeId" -> state["results"]["nodeId"]

    Non-string values are returned directly. Unknown strings are treated as
    literal values.

    Args:
        ref: Reference or literal value.
        state: Current workflow RunState.

    Returns:
        Any: Resolved value.

    Example:
        state = {
            "vars": {"route_key": "refund"},
            "last": "hello",
            "results": {"n1": 42},
        }

        assert _get_ref_value("vars.route_key", state) == "refund"
        assert _get_ref_value("last", state) == "hello"
        assert _get_ref_value("results.n1", state) == 42
    """
    if not isinstance(ref, str):
        return ref

    if ref == "last":
        return state.get("last")

    if ref == "route":
        return get_last_route(state)

    if ref.startswith("vars."):
        key = ref.split(".", 1)[1]
        return (state.get("vars") or {}).get(key)

    if ref.startswith("results."):
        key = ref.split(".", 1)[1]
        return (state.get("results") or {}).get(key)

    # fallback: literal string
    return ref


def eval_when(when: Any, state: Dict[str, Any]) -> bool:
    """
    Safely evaluate an edge condition without using Python eval().

    Supported condition operators:
        {"eq": [left, right]}      -> left == right
        {"ne": [left, right]}      -> left != right
        {"exists": ref}           -> resolved ref is not None
        {"and": [cond, cond]}      -> all conditions true
        {"or": [cond, cond]}       -> any condition true
        {"not": cond}             -> condition is false

    Backward compatibility:
        A plain string is treated as a route key:
            "refund" means get_last_route(state) == "refund"

    Args:
        when: Structured condition object.
        state: Current workflow RunState.

    Returns:
        bool: True if the condition allows the edge.

    Example:
        state = {"vars": {"route_key": "refund"}}

        assert eval_when({"eq": ["vars.route_key", "refund"]}, state) is True
        assert eval_when({"ne": ["vars.route_key", "shipping"]}, state) is True
    """
    if when is None:
        return True

    # allow simple string legacy (route key):
    if isinstance(when, str):
        return get_last_route(state) == when

    if not isinstance(when, dict) or not when:
        return False

    if "eq" in when:
        eq = when.get("eq")

        # must be list/tuple of length 2
        if not isinstance(eq, (list, tuple)) or len(eq) != 2:
            return False

        left, right = eq
        return _get_ref_value(left, state) == _get_ref_value(right, state)

    if "ne" in when:
        ne = when.get("ne")

        if not isinstance(ne, (list, tuple)) or len(ne) != 2:
            return False

        left, right = ne
        return _get_ref_value(left, state) != _get_ref_value(right, state)

    if "exists" in when:
        val = _get_ref_value(when["exists"], state)
        return val is not None

    if "and" in when:
        items = when["and"] or []
        return all(eval_when(x, state) for x in items)

    if "or" in when:
        items = when["or"] or []
        return any(eval_when(x, state) for x in items)

    if "not" in when:
        return not eval_when(when["not"], state)

    return False


def edge_is_allowed(edge: dict, state: Dict[str, Any]) -> bool:
    """
    Decide whether an edge is currently allowed.

    Supported conditional edge shapes:
      1. {"when": {"eq": ["vars.route_key", "refund"]}}
      2. {"condition": "refund"}                         # legacy
      3. {"data": {"route": "refund"}}                   # ReactFlow-friendly
      4. {"route": "refund"}                             # simple backend shape

    If no condition is present, the edge is allowed.
    """
    when = edge.get("when")
    if when is not None:
        return eval_when(when, state)

    route = (
        edge.get("route")
        or (edge.get("data") or {}).get("route")
        or edge.get("condition")
    )

    if route is not None:
        return str(_get_ref_value("vars.route_key", state) or "") == str(route)

    return True
