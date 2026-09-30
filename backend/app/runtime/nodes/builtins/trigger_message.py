from __future__ import annotations

from typing import Any, Dict

from app.runtime.nodes.types import NodeRunResult, RuntimeContext
from app.runtime.nodes.configs import TriggerMessageConfig


class TriggerMessageNode:
    """
    Start node for message-based workflows_route.

    This node emits the initial workflow input and stores it in state.vars["input"].

    Patch:
        vars.input = message
        last = message

    Example:
        config.input = "Where is my order?"

        result = {
            "output": "Where is my order?",
            "patch": {
                "vars": {"input": "Where is my order?"},
                "last": "Where is my order?",
            },
            "meta": {},
        }
    """

    async def run(
        self,
        ctx: RuntimeContext,
        state: Dict[str, Any],
        config: TriggerMessageConfig,
    ) -> NodeRunResult:
        """
        Return the configured trigger input as the first workflow output.

        Args:
            ctx: Runtime context.
            state: Current RunState snapshot.
            config: Trigger message config.

        Returns:
            NodeRunResult: Node result with output and patch.
        """
        runtime_input = state.get("vars", {}).get("input") or state.get("last") or ""

        msg = str(config.input).strip() if config.input else str(runtime_input).strip()

        patch = {
            "vars": {"input": msg},
            "last": msg,
        }

        return {"patch": patch, "output": msg, "meta": {}}
