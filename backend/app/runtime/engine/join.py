from __future__ import annotations

from typing import Dict, List


def compute_join_inputs(
    node_id: str,
    incoming_sources: List[str],
    outputs_by_node_id: Dict[str, object],
) -> List[dict]:
    """
    Join inputs = list of {"source": <node_id>, "output": <output>}
    This is injected into node config as "_join_inputs".
    """
    items = []
    for src in incoming_sources:
        if src in outputs_by_node_id:
            items.append({"source": src, "output": outputs_by_node_id[src]})
    return items
