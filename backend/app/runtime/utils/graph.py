from __future__ import annotations

from typing import Dict, List, Tuple


def build_graph(
    workflow: dict,
) -> Tuple[Dict[str, dict], List[dict], Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Convert React Flow workflow JSON into graph lookup structures.

    The executor and validator use these maps to quickly find nodes, parents,
    and children without repeatedly scanning the whole workflow.

    Args:
        workflow:
            React Flow workflow JSON:
            {
                "nodes": [
                    {"id": "t", "data": {"nodeType": "trigger.message"}},
                    {"id": "r", "data": {"nodeType": "response"}},
                ],
                "edges": [
                    {"source": "t", "target": "r"},
                ],
            }

    Returns:
        tuple:
            nodes_by_id:
                {"node_id": node_def}

            edges:
                Original edge list.

            outgoing:
                {"source_node_id": ["target_node_id", ...]}

            incoming:
                {"target_node_id": ["source_node_id", ...]}

    Notes:
        Invalid edges are ignored here:
            - missing source/target
            - source or target not found in nodes

        Validation errors are handled separately in validator.py.

    Example:
        nodes_by_id, edges, outgoing, incoming = build_graph(workflow)

        assert outgoing["t"] == ["r"]
        assert incoming["r"] == ["t"]
    """
    nodes = workflow.get("nodes") or []
    edges = workflow.get("edges") or []

    nodes_by_id: Dict[str, dict] = {n["id"]: n for n in nodes}

    outgoing: Dict[str, List[str]] = {nid: [] for nid in nodes_by_id}
    incoming: Dict[str, List[str]] = {nid: [] for nid in nodes_by_id}

    for e in edges:
        src = e.get("source")
        tgt = e.get("target")
        if not src or not tgt:
            continue
        if src not in nodes_by_id or tgt not in nodes_by_id:
            continue
        outgoing[src].append(tgt)
        incoming[tgt].append(src)

    return nodes_by_id, edges, outgoing, incoming


def find_trigger_node_id(nodes_by_id: Dict[str, dict]) -> str | None:
    """
    Return the first trigger.message node id.

    The v1 runtime expects workflows_route to start from a trigger.message node.
    Strict validation ensures there is exactly one trigger, but this helper simply
    returns the first one found.

    Args:
        nodes_by_id: Mapping of node_id to node definition.

    Returns:
        str | None: Trigger node id, or None if no trigger exists.

    Example:
        trigger_id = find_trigger_node_id({
            "t": {"id": "t", "data": {"nodeType": "trigger.message"}},
            "r": {"id": "r", "data": {"nodeType": "response"}},
        })

        assert trigger_id == "t"
    """
    for nid, n in nodes_by_id.items():
        nt = (n.get("data") or {}).get("nodeType")
        if nt == "trigger.message":
            return nid
    return None


def get_parents(node_id: str, edges: List[dict]) -> List[str]:
    """
    Return parent/source node ids for a node.

    This scans the edge list and returns all sources where:
        edge["target"] == node_id

    Args:
        node_id: Node whose parents should be returned.
        edges: Workflow edge list.

    Returns:
        list[str]: Parent node ids.

    Example:
        parents = get_parents(
            "r",
            [{"source": "t", "target": "r"}],
        )

        assert parents == ["t"]
    """
    parents: List[str] = []
    for e in edges:
        if e.get("target") == node_id and e.get("source"):
            parents.append(e["source"])
    return parents
