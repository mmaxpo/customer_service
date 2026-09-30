from __future__ import annotations

from typing import Any, Dict


RunState = Dict[str, Any]


def merge_patch(state: RunState, patch: dict) -> RunState:
    """
    Merge a patch dictionary into dict-based RunState.

    This function keeps the runtime standardized on dictionary state.

    Merge rules:
        - "vars" is shallow-merged into state["vars"]
        - dict values are shallow-merged when existing state value is also dict
        - other values overwrite the existing value
        - required RunState keys are preserved

    Args:
        state: Dict-based workflow RunState.
        patch: Partial state update returned by a node.

    Returns:
        RunState: Updated state dictionary.

    Example:
        state = {"vars": {"input": "hello"}}
        patch = {"vars": {"intent": "refund"}}

        state = merge_patch(state, patch)

        assert state["vars"] == {
            "input": "hello",
            "intent": "refund",
        }
    """
    if not patch:
        return state

    out = dict(state)

    for key, value in patch.items():
        if key == "vars" and isinstance(value, dict):
            out.setdefault("vars", {})
            out["vars"] = {**out["vars"], **value}
        elif isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **value}
        else:
            out[key] = value

    out.setdefault("vars", {})
    out.setdefault("memory", {})
    out.setdefault("results", {})
    out.setdefault("meta", {"events": [], "node_meta_by_id": {}})
    out.setdefault("errors", {})
    out.setdefault("last", None)

    return out
