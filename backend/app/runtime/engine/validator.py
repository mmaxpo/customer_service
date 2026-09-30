# app/runtime/engine/validator.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from app.runtime.utils.graph import build_graph


@dataclass
class ValidationError:
    code: str
    message: str
    details: dict

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "details": self.details}


ROUTER_NODE_TYPES = {"router.rules", "router.llm", "control.loop"}


def _node_type(node_def: dict) -> str:
    return (node_def.get("data") or {}).get("nodeType") or ""


def _find_triggers(nodes_by_id: Dict[str, dict]) -> List[str]:
    return [nid for nid, n in nodes_by_id.items() if _node_type(n) == "trigger.message"]


def _reachable_from(start_id: str, outgoing: Dict[str, List[str]]) -> Set[str]:
    seen: Set[str] = set()
    stack = [start_id]
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        for nxt in outgoing.get(nid, []):
            if nxt not in seen:
                stack.append(nxt)
    return seen


def _has_cycle(
    nodes_by_id: Dict[str, dict], outgoing: Dict[str, List[str]]
) -> Tuple[bool, List[str]]:
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {nid: WHITE for nid in nodes_by_id.keys()}
    parent: Dict[str, Optional[str]] = {nid: None for nid in nodes_by_id.keys()}

    def build_cycle(u: str, v: str) -> List[str]:
        path = [v]
        cur = u
        while cur is not None and cur != v:
            path.append(cur)
            cur = parent.get(cur)
        path.append(v)
        path.reverse()
        return path

    def dfs(u: str) -> Optional[List[str]]:
        color[u] = GRAY
        for v in outgoing.get(u, []):
            if v not in color:
                continue
            if color[v] == WHITE:
                parent[v] = u
                cyc = dfs(v)
                if cyc:
                    return cyc
            elif color[v] == GRAY:
                return build_cycle(u, v)
        color[u] = BLACK
        return None

    for nid in nodes_by_id.keys():
        if color[nid] == WHITE:
            cyc = dfs(nid)
            if cyc:
                return True, cyc
    return False, []


def _validate_when_shape(when: object) -> Optional[dict]:
    """
    v1 UI contract (Dropdown-only):
      when = {"eq": ["vars.route_key", "<route>"]}

    Return a dict error details if invalid, else None.
    """
    if when is None:
        return None
    if isinstance(when, str):
        # legacy supported in runtime, but UI should not write it.
        return {"reason": "legacy_string_not_allowed", "got": when}

    if not isinstance(when, dict) or not when:
        return {
            "reason": "when_must_be_non_empty_object",
            "got_type": type(when).__name__,
        }

    # Only allow eq in v1
    if set(when.keys()) != {"eq"}:
        return {
            "reason": "only_eq_allowed_in_v1",
            "got_keys": sorted(list(when.keys())),
        }

    eq = when.get("eq")
    if not isinstance(eq, list) or len(eq) != 2:
        return {"reason": "eq_must_be_list_len_2", "got": eq}

    left, right = eq[0], eq[1]
    if left != "vars.route_key":
        return {"reason": "left_must_be_vars.route_key", "got_left": left}

    if not isinstance(right, str) or not right.strip():
        return {"reason": "right_must_be_non_empty_string", "got_right": right}

    return None


def validate_nodes_shape(nodes: object) -> list[ValidationError]:
    """
    Validate the basic shape of workflow nodes.

    Checks:
        - nodes is a non-empty list
        - each node has a valid string id
        - node ids are unique
        - each node has data.nodeType

    Returns:
        list[ValidationError]: Node validation errors.

    Example:
        errors = validate_nodes_shape([
            {"id": "t", "data": {"nodeType": "trigger.message"}},
            {"id": "r", "data": {"nodeType": "response"}},
        ])

        assert errors == []
    """
    if not isinstance(nodes, list) or not nodes:
        return [
            ValidationError(
                code="no_nodes",
                message="Workflow must include a non-empty 'nodes' list.",
                details={"got_type": type(nodes).__name__},
            )
        ]

    errors: list[ValidationError] = []
    seen_ids: set[str] = set()

    for index, node in enumerate(nodes):
        node_id = node.get("id")

        if not node_id or not isinstance(node_id, str):
            errors.append(
                ValidationError(
                    code="node_missing_id",
                    message="Node is missing a valid string 'id'.",
                    details={"index": index},
                )
            )
            continue

        if node_id in seen_ids:
            errors.append(
                ValidationError(
                    code="duplicate_node_id",
                    message="Duplicate node id.",
                    details={"node_id": node_id},
                )
            )

        seen_ids.add(node_id)

        node_type = _node_type(node)
        if not node_type:
            errors.append(
                ValidationError(
                    code="node_missing_type",
                    message="Node is missing data.nodeType.",
                    details={"node_id": node_id},
                )
            )

    return errors


def validate_loop_nodes(nodes_by_id: dict) -> list[ValidationError]:
    """
    Validate control.loop node configuration.

    Checks:
        - reset_node_ids exists and is non-empty
        - every reset_node_id references an existing node
        - max_iters is an integer >= 1 when provided

    Example:
        errors = validate_loop_nodes({
            "loop": {
                "id": "loop",
                "data": {
                    "nodeType": "control.loop",
                    "reset_node_ids": ["work"],
                    "max_iters": 3,
                },
            },
            "work": {"id": "work", "data": {"nodeType": "llm.generate"}},
        })

        assert errors == []
    """
    errors: list[ValidationError] = []

    for node_id, node_def in nodes_by_id.items():
        if _node_type(node_def) != "control.loop":
            continue

        data = node_def.get("data") or {}
        reset_ids = data.get("reset_node_ids") or []
        max_iters = data.get("max_iters")

        if not isinstance(reset_ids, list) or not reset_ids:
            errors.append(
                ValidationError(
                    code="invalid_loop_reset",
                    message="control.loop must include non-empty reset_node_ids list.",
                    details={"node_id": node_id, "reset_node_ids": reset_ids},
                )
            )
        else:
            missing = [x for x in reset_ids if x not in nodes_by_id]
            if missing:
                errors.append(
                    ValidationError(
                        code="invalid_loop_reset",
                        message="control.loop reset_node_ids contains unknown node ids.",
                        details={"node_id": node_id, "missing": missing},
                    )
                )

        if max_iters is not None:
            try:
                parsed_max_iters = int(max_iters)
                if parsed_max_iters < 1:
                    raise ValueError()
            except Exception:
                errors.append(
                    ValidationError(
                        code="invalid_loop_max_iters",
                        message="control.loop max_iters must be an integer >= 1.",
                        details={"node_id": node_id, "max_iters": max_iters},
                    )
                )

    return errors


def validate_edges_shape_and_endpoints(
    edges: object,
    nodes_by_id: dict,
) -> list[ValidationError]:
    """
    Validate edges structure and endpoint correctness.

    Checks:
        - edges is a list
        - each edge has source and target
        - source/target exist in nodes
        - no self-loops
        - conditional edges only originate from router nodes
        - 'when' follows v1 contract

    Returns:
        list[ValidationError]

    Example:
        errors = validate_edges_shape_and_endpoints(
            edges=[{"source": "a", "target": "b"}],
            nodes_by_id={"a": {...}, "b": {...}},
        )

        assert errors == []
    """
    errors: list[ValidationError] = []

    if not isinstance(edges, list):
        errors.append(
            ValidationError(
                code="edges_not_list",
                message="Workflow 'edges' must be a list.",
                details={"got_type": type(edges).__name__},
            )
        )
        return errors

    for index, edge in enumerate(edges):
        src = edge.get("source")
        tgt = edge.get("target")

        if not src or not tgt:
            errors.append(
                ValidationError(
                    code="edge_missing_endpoint",
                    message="Edge must include 'source' and 'target'.",
                    details={"index": index},
                )
            )
            continue

        if src not in nodes_by_id or tgt not in nodes_by_id:
            errors.append(
                ValidationError(
                    code="edge_invalid_endpoint",
                    message="Edge endpoints must reference existing nodes.",
                    details={"index": index, "source": src, "target": tgt},
                )
            )
            continue

        if src == tgt:
            errors.append(
                ValidationError(
                    code="edge_self_loop",
                    message="Self-loop edges are not allowed (source == target).",
                    details={"index": index, "node_id": src},
                )
            )

        has_condition = (
            edge.get("condition") is not None and edge.get("condition") != ""
        )
        has_when = "when" in edge and edge.get("when") is not None

        if has_condition or has_when:
            src_type = _node_type(nodes_by_id[src])

            if src_type not in ROUTER_NODE_TYPES:
                errors.append(
                    ValidationError(
                        code="conditional_edge_from_non_router",
                        message="Edge has condition/when but source node is not a router.* node.",
                        details={
                            "index": index,
                            "source": src,
                            "source_type": src_type,
                            "condition": edge.get("condition"),
                            "when": edge.get("when"),
                        },
                    )
                )
            else:
                if has_when:
                    bad = _validate_when_shape(edge.get("when"))
                    if bad:
                        errors.append(
                            ValidationError(
                                code="invalid_when",
                                message="Edge 'when' is invalid for v1 contract.",
                                details={
                                    "index": index,
                                    "when": edge.get("when"),
                                    "error": bad,
                                },
                            )
                        )

    return errors


def validate_trigger_count(
    *,
    triggers: list[str],
    strict: bool,
) -> list[ValidationError]:
    """
    Validate workflow trigger count.

    In strict v1 mode:
        exactly one trigger.message node is required.

    In non-strict mode:
        at least one trigger.message node is required.

    Example:
        errors = validate_trigger_count(
            triggers=["trigger_1"],
            strict=True,
        )

        assert errors == []
    """
    if strict:
        if len(triggers) != 1:
            return [
                ValidationError(
                    code="invalid_trigger_count",
                    message="Workflow must contain exactly one trigger.message node (for v1 strict mode).",
                    details={"found": triggers, "count": len(triggers)},
                )
            ]

        return []

    if len(triggers) < 1:
        return [
            ValidationError(
                code="missing_trigger",
                message="Workflow must contain at least one trigger.message node.",
                details={},
            )
        ]

    return []


def validate_cycles(
    *,
    nodes_by_id: dict,
    outgoing: dict,
) -> list[ValidationError]:
    """
    Validate that the workflow has no uncontrolled cycles.

    Normal workflows_route must be DAGs. Cycles are only allowed when the detected
    cycle contains a control.loop node, because control.loop is the explicit
    runtime mechanism for controlled repetition.

    Example:
        errors = validate_cycles(
            nodes_by_id=nodes_by_id,
            outgoing=outgoing,
        )

        assert errors == []
    """
    has_cycle, cycle_path = _has_cycle(nodes_by_id, outgoing)

    if not has_cycle:
        return []

    loop_nodes = {
        node_id
        for node_id, node_def in nodes_by_id.items()
        if _node_type(node_def) == "control.loop"
    }
    cycle_has_loop = any(node_id in loop_nodes for node_id in (cycle_path or []))

    if cycle_has_loop:
        return []

    return [
        ValidationError(
            code="cycle_detected",
            message="Workflow contains a cycle (DAG required unless controlled by control.loop).",
            details={"cycle_path": cycle_path},
        )
    ]


def validate_reachable_response(
    *,
    nodes_by_id: dict,
    outgoing: dict,
    triggers: list[str],
) -> list[ValidationError]:
    """
    Validate that at least one response node is reachable from the trigger.

    A valid workflow must eventually produce a final response. This check first
    verifies that at least one response node exists, then checks reachability
    from the first trigger.

    Example:
        errors = validate_reachable_response(
            nodes_by_id=nodes_by_id,
            outgoing=outgoing,
            triggers=["trigger"],
        )

        assert errors == []
    """
    response_ids = [
        node_id
        for node_id, node_def in nodes_by_id.items()
        if _node_type(node_def) == "response"
    ]

    if not response_ids:
        return [
            ValidationError(
                code="missing_response",
                message="Workflow must contain at least one response node.",
                details={},
            )
        ]

    if not triggers:
        return []

    start = triggers[0]
    reachable = _reachable_from(start, outgoing)
    reachable_responses = [
        response_id for response_id in response_ids if response_id in reachable
    ]

    if reachable_responses:
        return []

    return [
        ValidationError(
            code="unreachable_response",
            message="No response node is reachable from the trigger.",
            details={
                "trigger": start,
                "response_nodes": response_ids,
            },
        )
    ]


def validate_workflow(workflow: dict, *, strict: bool = True) -> List[ValidationError]:
    """
    Validate a workflow definition before runtime execution.

    This is the main validation entry point used by the workflow executor before
    building and running the DAG. It performs structural checks first, then graph
    checks.

    Validation steps:
        1. Validate nodes shape.
        2. Build graph maps.
        3. Validate control.loop nodes.
        4. Validate edges.
        5. Validate trigger count.
        6. Validate uncontrolled cycles.
        7. Validate response reachability.

    strict=True:
        - exactly one trigger.message node is required
        - at least one response node is required
        - at least one response must be reachable from the trigger
        - cycles are rejected unless controlled by control.loop
        - edge endpoints must reference real nodes
        - conditional edges must come from router/control nodes

    strict=False:
        - at least one trigger.message node is required
        - response and reachability are still validated
        - useful later for multi-trigger or more flexible workflows_route

    Args:
        workflow:
            React Flow workflow JSON:
            {
                "nodes": [...],
                "edges": [...]
            }

        strict:
            Whether to apply strict v1 workflow rules.

    Returns:
        list[ValidationError]:
            Empty list means the workflow is valid.
            Non-empty list means execution should stop and return validation errors.

    Example:
        workflow = {
            "nodes": [
                {"id": "t", "data": {"nodeType": "trigger.message"}},
                {"id": "r", "data": {"nodeType": "response"}},
            ],
            "edges": [
                {"source": "t", "target": "r"},
            ],
        }

        errors = validate_workflow(workflow)

        assert errors == []
    """
    errors: List[ValidationError] = []

    nodes = workflow.get("nodes") or []
    edges = workflow.get("edges") or []

    # ---- basic nodes validation ----
    node_errors = validate_nodes_shape(nodes)
    if node_errors and any(err.code == "no_nodes" for err in node_errors):
        return node_errors

    errors.extend(node_errors)

    # build graph even if we already found some errors (best-effort)
    nodes_by_id, edges_norm, outgoing, incoming = build_graph(workflow)

    # ---- loop nodes validation ----
    errors.extend(validate_loop_nodes(nodes_by_id))

    # ---- edges validation ----
    edge_errors = validate_edges_shape_and_endpoints(edges, nodes_by_id)
    errors.extend(edge_errors)

    # important: preserve early return behavior
    if any(e.code == "edges_not_list" for e in edge_errors):
        return errors

    # ---- trigger validation ----
    triggers = _find_triggers(nodes_by_id)
    errors.extend(validate_trigger_count(triggers=triggers, strict=strict))

    # ---- cycle detection ----
    errors.extend(
        validate_cycles(
            nodes_by_id=nodes_by_id,
            outgoing=outgoing,
        )
    )

    errors.extend(
        validate_reachable_response(
            nodes_by_id=nodes_by_id,
            outgoing=outgoing,
            triggers=triggers,
        )
    )

    return errors
