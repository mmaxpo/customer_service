from __future__ import annotations

from typing import Any, Dict

from app.runtime.nodes.types import NodeRunResult, RuntimeContext
from app.runtime.nodes.configs import SetVariableConfig


class SetVariableNode:
    """
    Data node that writes a value into workflow variables.

    Writes:
        state.vars[config.key] = config.value
        state.last = config.value

    If save_as is provided, it also writes:
        state.vars[config.save_as] = config.value

    Example:
        config.key = "intent"
        config.value = "refund"

        patch = {
            "vars": {"intent": "refund"},
            "last": "refund",
        }
    """

    async def run(
        self,
        ctx: RuntimeContext,
        state: Dict[str, Any],
        config: SetVariableConfig,
    ) -> NodeRunResult:
        """
        Write config.value into state.vars[config.key].

        Args:
            ctx: Runtime context.
            state: Current RunState snapshot.
            config: Set variable config.

        Returns:
            NodeRunResult: Node output and patch.
        """
        patch_vars = {config.key: config.value}

        if config.save_as:
            patch_vars[config.save_as] = config.value

        patch = {
            "vars": patch_vars,
            "last": config.value,
        }

        return {"patch": patch, "output": config.value, "meta": {}}
