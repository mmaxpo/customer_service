from __future__ import annotations

from typing import Any

from app.runtime.nodes.registry.models import NodeRegistration


def _placeholder_for_schema(prop: dict) -> Any:
    """
    Create a safe placeholder value from a JSON schema property.

    Used when building frontend default configs for Pydantic models that have
    required fields but no default values.

    Mapping:
        string  -> ""
        integer -> 0
        number  -> 0
        boolean -> False
        array   -> []
        object  -> {}

    If enum exists, the first enum value is used.

    Example:
        value = _placeholder_for_schema({"type": "string"})
        assert value == ""

        value = _placeholder_for_schema({"enum": ["open", "closed"]})
        assert value == "open"
    """
    if not isinstance(prop, dict):
        return None

    enum = prop.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]

    t = prop.get("type")

    if isinstance(t, list) and t:
        t = next((x for x in t if x != "null"), t[0])

    if t == "string":
        return ""
    if t == "integer":
        return 0
    if t == "number":
        return 0
    if t == "boolean":
        return False
    if t == "array":
        return []
    if t == "object":
        return {}

    for k in ("anyOf", "oneOf"):
        opts = prop.get(k)
        if isinstance(opts, list) and opts:
            return _placeholder_for_schema(opts[0])

    return None


def default_config_for(type_name: str, reg: NodeRegistration) -> dict:
    """
    Build frontend-friendly default config for a registered node type.

    The frontend uses this default config when a user drags a node onto the
    React Flow canvas.

    Strategy:
        1. Always include nodeType and node_type.
        2. If no config model exists, return only the base config.
        3. Try to instantiate the Pydantic model using defaults.
        4. If required fields prevent instantiation, use JSON schema to build
           placeholder values.
        5. Apply hardcoded UX overrides for special nodes.

    Args:
        type_name: Node type string, e.g. "router.llm".
        reg: NodeRegistration for that type.

    Returns:
        dict: Default node config.

    Example:
        default_config = _default_config_for("response", reg)

        assert default_config["nodeType"] == "response"
    """
    base: dict = {"nodeType": type_name, "node_type": type_name}

    if reg.config_model is None:
        return base

    try:
        inst = reg.config_model()
        d = inst.model_dump(exclude_none=True)
        return {**base, **d}
    except Exception:
        pass

    try:
        schema = reg.config_model.model_json_schema() or {}
        props = schema.get("properties") or {}
        required = schema.get("required") or []

        out = dict(base)

        for k, prop in props.items():
            if isinstance(prop, dict) and "default" in prop:
                out[k] = prop["default"]

        for k in required:
            if k in ("node_type", "nodeType"):
                continue
            if k not in out:
                out[k] = _placeholder_for_schema(props.get(k) or {})

        if type_name == "subworkflow.call":
            out.setdefault("workflow", {"nodes": [], "edges": []})

        if type_name == "router.llm":
            choices = out.get("choices")
            if not isinstance(choices, list) or len(choices) < 2:
                out["choices"] = ["default", "billing"]

        return out
    except Exception:
        return base
