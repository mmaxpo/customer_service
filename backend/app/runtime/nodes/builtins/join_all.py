from __future__ import annotations

from typing import Any, Dict

from app.runtime.nodes.types import NodeRunResult, RuntimeContext
from app.runtime.nodes.configs import JoinAllConfig


class JoinAllNode:
    """
    Join node for combining multiple parent outputs.

    The engine injects parent outputs into:
        ctx.node_data["_join_inputs"]

    Example:
        Parent A output = "hello"
        Parent B output = "world"

        ctx.node_data["_join_inputs"] = ["hello", "world"]

    Modes:
        list:
            output = ["hello", "world"]

        concat_text:
            output = "hello\\nworld"

    Optional:
        If config.save_as is set, output is saved to state.vars[save_as].
    """

    async def run(
        self, ctx: RuntimeContext, state: Dict[str, Any], config: JoinAllConfig
    ) -> NodeRunResult:

        vars_ = state.get("vars") or {}

        node_data = getattr(ctx, "node_data", {}) or {}

        inputs = node_data.get("_join_inputs")

        input_keys = node_data.get("_join_input_keys")

        if inputs is None:
            inputs = vars_.get("_join_inputs")

        if input_keys is None:
            input_keys = vars_.get("_join_input_keys")

        if inputs is None:
            inputs = []

        if not isinstance(inputs, list):
            inputs = [inputs]

        if not isinstance(input_keys, list):
            input_keys = []

        if config.mode == "concat_text":
            out = config.separator.join(str(x) for x in inputs if x is not None)

        elif config.mode == "object":
            out = {}

            for index, value in enumerate(inputs):
                if value is None or value == "":
                    continue

                key = (
                    str(input_keys[index])
                    if index < len(input_keys) and input_keys[index]
                    else f"input_{index + 1}"
                )

                out[key] = value

        else:
            out = inputs

        patch = {"last": out}

        if config.save_as:
            patch["vars"] = {config.save_as: out}

        return {
            "patch": patch,
            "output": out,
            "meta": {
                "joined": len(inputs),
                "mode": config.mode,
            },
        }
