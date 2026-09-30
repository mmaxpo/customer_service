# app/runtime/utils/template.py
from __future__ import annotations

import re
from typing import Any, Dict

# Matches {{ path.like.this }} anywhere in a string
_TPL_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def _normalize_path(path: str) -> str:
    """
    Normalize template variable paths before lookup.

    Supported input forms:
        "customer.name"              -> "customer.name"
        "orders[0].tracking_number"  -> "orders.0.tracking_number"
        "vars.customer.name"         -> "customer.name"

    This keeps template syntax flexible while still resolving against state["vars"].

    Args:
        path: Raw template path from inside {{ ... }}.

    Returns:
        str: Normalized dot-path.

    Example:
        assert _normalize_path("orders[0].id") == "orders.0.id"
        assert _normalize_path("vars.customer.email") == "customer.email"
    """
    # allow "ws.results[0].link" -> "ws.results.0.link"
    path = re.sub(r"\[(\d+)\]", r".\1", path.strip())
    # allow "vars.ws.results.0.link" -> "ws.results.0.link"
    if path.startswith("vars."):
        path = path[len("vars.") :]
    return path


def get_by_path(obj: Any, path: str) -> Any:
    """
    Resolve a normalized dot-path through nested dict/list data.

    Supports:
        dict keys:
            customer.email

        list indexes:
            orders.0.id

        bracket indexes before normalization:
            orders[0].id

    Attribute access is intentionally not supported. This keeps template
    resolution deterministic and safer.

    Args:
        obj: Root object, usually state["vars"].
        path: Dot-path or bracket-path.

    Returns:
        Any:
            Resolved value, or None when the path cannot be resolved.

    Example:
        data = {
            "customer": {"email": "a@example.com"},
            "orders": [{"id": "ord_1"}],
        }

        assert get_by_path(data, "customer.email") == "a@example.com"
        assert get_by_path(data, "orders[0].id") == "ord_1"
        assert get_by_path(data, "missing.key") is None
    """
    cur = obj
    path = _normalize_path(path)

    for part in path.split("."):
        if cur is None:
            return None

        if isinstance(cur, list) and part.isdigit():
            i = int(part)
            if i < 0 or i >= len(cur):
                return None
            cur = cur[i]
            continue

        if isinstance(cur, dict):
            cur = cur.get(part)
            continue

        # we don't support attribute traversal here (keep deterministic)
        return None

    return cur


def render_template(value: Any, vars_: Dict[str, Any]) -> Any:
    """
    Recursively render {{ path }} templates using workflow variables.

    This is used before node config is parsed, so node configs can reference
    previous node outputs or shared variables.

    Rendering rules:
        1. None stays None.
        2. Exact template string returns the real object:
               "{{ customer }}" -> dict/list/string/etc.
        3. Partial template string returns a string:
               "Hello {{ customer.name }}" -> "Hello Mehdi"
        4. Missing values become "" in partial strings.
        5. Lists and dicts are rendered recursively.
        6. Non-string scalar values are returned unchanged.

    Args:
        value:
            Any config value: str, list, dict, int, bool, None, etc.

        vars_:
            Workflow variable namespace, usually state["vars"].

    Returns:
        Any:
            Rendered value.

    Example exact object:
        vars_ = {"hits": [{"title": "Refund Policy"}]}

        result = render_template("{{ hits }}", vars_)

        assert result == [{"title": "Refund Policy"}]

    Example partial string:
        vars_ = {"customer": {"name": "Mehdi"}}

        result = render_template("Hello {{ customer.name }}", vars_)

        assert result == "Hello Mehdi"

    Example recursive dict:
        vars_ = {"email": "a@example.com"}

        result = render_template(
            {"to": "{{ email }}", "subject": "Hi"},
            vars_,
        )

        assert result == {"to": "a@example.com", "subject": "Hi"}
    """
    if value is None:
        return None

    if isinstance(value, str):
        s = value.strip()

        # exact match -> return object, not string
        m = re.fullmatch(r"\{\{\s*([^}]+?)\s*\}\}", s)
        if m:
            return get_by_path(vars_, m.group(1))

        # partial substitution -> string
        def _sub(mm: re.Match) -> str:
            v = get_by_path(vars_, mm.group(1))
            return "" if v is None else str(v)

        return _TPL_RE.sub(_sub, value)

    if isinstance(value, list):
        return [render_template(x, vars_) for x in value]

    if isinstance(value, dict):
        return {k: render_template(v, vars_) for k, v in value.items()}

    return value
