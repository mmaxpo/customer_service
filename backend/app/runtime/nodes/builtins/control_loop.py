from __future__ import annotations

from typing import Any, Dict

from app.runtime.nodes.types import NodeRunResult, RuntimeContext
from app.runtime.nodes.configs import LoopConfig


class ControlLoopNode:
    """
    Controlled loop node for safe bounded repetition.

    This node decides whether a loop should continue or stop.

    It writes:
        state.vars[loop_key] = current_iteration
        state.vars["route_key"] = continue_route | stop_route
        state.last = route

    If route == continue_route, it also returns:
        result["loop_reset"] = reset_node_ids

    The executor uses loop_reset to mark selected nodes as runnable again.

    Example:
        max_iters = 3

        Visit 1 -> route = "continue"
        Visit 2 -> route = "continue"
        Visit 3 -> route = "stop"
    """

    async def run(
        self, ctx: RuntimeContext, state: Dict[str, Any], config: LoopConfig
    ) -> NodeRunResult:
        vars_ = state.get("vars") or {}

        cur = vars_.get(config.loop_key, 0)
        try:
            cur_int = int(cur or 0)
        except Exception:
            cur_int = 0

        # increment on each visit
        cur_int += 1

        if cur_int >= config.max_iters:
            route = config.stop_route
        else:
            route = config.continue_route

        patch_vars = {
            config.loop_key: cur_int,
            "route_key": route,
        }

        if config.save_as:
            patch_vars[config.save_as] = route

        patch = {
            "vars": patch_vars,
            "last": route,
        }

        result: Dict[str, Any] = {
            "patch": patch,
            "output": route,
            "route": route,
            "meta": {
                "loop_key": config.loop_key,
                "loop_count": cur_int,
                "route": route,
            },
        }

        # executor will use this ONLY when route==continue
        if route == config.continue_route:
            result["loop_reset"] = list(config.reset_node_ids or [])

        return result
