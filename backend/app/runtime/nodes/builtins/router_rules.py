from __future__ import annotations

from typing import Any, Dict

from app.runtime.nodes.types import NodeRunResult, RuntimeContext
from app.runtime.nodes.configs import RouterRulesConfig


def _eval_rule(expr: str, state: Dict[str, Any]) -> bool:
    """
    Evaluate a simple rule expression against RunState.

    Supported MVP syntax:
        vars.intent == 'billing'
        last == 'refund'

    This intentionally does not use eval(), so it is safer but limited.

    Example:
        state = {"vars": {"intent": "billing"}, "last": "hello"}

        assert _eval_rule("vars.intent == 'billing'", state) is True
        assert _eval_rule("last == 'refund'", state) is False
    """
    expr = expr.strip()
    vars_ = state.get("vars") or {}
    last = state.get("last")

    # vars.foo == 'bar'
    if expr.startswith("vars.") and "==" in expr:
        left, right = expr.split("==", 1)
        key = left.strip().replace("vars.", "", 1).strip()
        expected = right.strip().strip('"').strip("'")
        return str(vars_.get(key, "")) == expected

    # last == 'bar'
    if expr.startswith("last") and "==" in expr:
        _, right = expr.split("==", 1)
        expected = right.strip().strip('"').strip("'")
        return str(last or "") == expected

    return False


class RouterRulesNode:
    """
    Rule-based router node.

    Reads workflow state, evaluates rules in order, and emits the first matching
    route. If no rule matches, it emits config.default_route.

    Writes:
        state.vars["route_key"] = route
        state.last = route

    Also returns:
        result["route"] = route

    The engine records this route and uses it to evaluate outgoing conditional
    edges.

    Example:
        rules = [
            {"when": "vars.intent == 'refund'", "route": "refund"}
        ]

        If state.vars["intent"] == "refund":
            output = "refund"
    """

    async def run(
        self, ctx: RuntimeContext, state: Dict[str, Any], config: RouterRulesConfig
    ) -> NodeRunResult:
        route = config.default_route
        for rule in config.rules:
            if _eval_rule(rule.when, state):
                route = rule.route
                break

        patch_vars = {"route_key": route}

        if config.save_as:
            patch_vars[config.save_as] = route

        patch = {
            "vars": patch_vars,
            "last": route,
        }
        if config.save_as:
            patch["vars"] = {**patch["vars"], config.save_as: route}

        return {
            "patch": patch,
            "output": route,
            "route": route,
            "meta": {"route": route},
        }
