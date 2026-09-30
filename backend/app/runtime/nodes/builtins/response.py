from __future__ import annotations

import json
from typing import Any, Dict

from app.runtime.nodes.types import NodeRunResult, RuntimeContext
from app.runtime.nodes.configs import ResponseConfig
from app.runtime.utils.template import get_by_path


class ResponseNode:
    """
    Final output node for workflows_route.

    This node chooses the final answer from:
        - state["last"]
        - state["vars"][answer_key]
        - nested state["vars"] path via from_var

    It writes the selected answer to:
        state.vars["answer"]
        state.last

    Example:
        state = {"last": "Your order is shipped", "vars": {}}
        config.answer_from = "last"

        output = "Your order is shipped"
    """

    async def run(
        self,
        ctx: RuntimeContext,
        state: Dict[str, Any],
        config: ResponseConfig,
    ) -> NodeRunResult:
        """
        Build the final workflow answer.

        Args:
            ctx: Runtime context.
            state: Current RunState snapshot.
            config: Response config.

        Returns:
            NodeRunResult: Final answer result.
        """
        vars_ = state.get("vars") or {}
        answer_obj = self._resolve_answer(state=state, vars_=vars_, config=config)
        answer_out = self._format_answer(answer_obj=answer_obj, config=config)

        patch_vars = {"answer": answer_out}
        if getattr(config, "save_as", None):
            patch_vars[config.save_as] = answer_out

        patch = {
            "vars": patch_vars,
            "last": answer_out,
        }

        return {"patch": patch, "output": answer_out, "meta": {}}

    def _resolve_answer(
        self,
        *,
        state: Dict[str, Any],
        vars_: Dict[str, Any],
        config: ResponseConfig,
    ) -> Any:
        """
        Resolve answer object from state according to ResponseConfig.
        """
        last = state.get("last")

        if getattr(config, "from_var", None):
            return get_by_path(vars_, config.from_var)

        if config.answer_from == "vars":
            return vars_.get(config.answer_key, "")

        return last if last is not None else ""

    def _format_answer(self, *, answer_obj: Any, config: ResponseConfig) -> Any:
        """
        Convert answer object to final output format.
        """
        if getattr(config, "raw", False):
            return answer_obj

        if getattr(config, "as_json", False):
            return json.dumps(answer_obj, ensure_ascii=False, default=str)

        return "" if answer_obj is None else str(answer_obj)
