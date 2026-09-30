from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from app.runtime.nodes.types import NodeRunResult, RuntimeContext
from app.runtime.nodes.configs import RouterLLMConfig


class RouterLLMNode:
    """
    LLM-based router node.

    Reads user input from state and asks an LLM/agent to choose one route from
    config.choices.

    Writes:
        state.vars["route_key"] = route
        state.last = route

    Also returns:
        result["route"] = route

    Safety:
        If the LLM returns a route not listed in config.choices, the node falls
        back to config.choices[0].

    Example:
        choices = ["refund", "shipping", "default"]

        If LLM returns "refund":
            route = "refund"
    """

    async def run(
        self, ctx: RuntimeContext, state: Dict[str, Any], config: RouterLLMConfig
    ) -> NodeRunResult:
        vars_ = state.get("vars") or {}
        last = state.get("last")

        if config.input_from == "vars":
            user_text = str(vars_.get(config.input_key, "")).strip()
        else:
            user_text = str(last or "").strip()

        agent = ctx.app.state.knowledge_agent  # or a smaller router model later: agent = ctx.tools.router_agent or ctx.app.state.knowledge_agent

        prompt = (
            f"{config.instruction}\n\n"
            f"Allowed routes: {', '.join(config.choices)}\n\n"
            f"Input:\n{user_text}\n\n"
            f"Return ONLY one route key."
        )

        out = await agent.ainvoke(
            {
                "messages": [
                    SystemMessage(content="You are a routing classifier."),
                    HumanMessage(content=prompt),
                ]
            },
            config={
                "configurable": {"user_id": ctx.user_id, "thread_id": ctx.thread_id}
            },
        )
        route = (out["messages"][-1].content or "").strip()

        if route not in set(config.choices):
            route = config.choices[0]  # safe fallback

        patch_vars = {"route_key": route}

        if config.save_as:
            patch_vars[config.save_as] = route

        patch = {
            "vars": patch_vars,
            "last": route,
        }

        return {
            "patch": patch,
            "output": route,
            "route": route,
            "meta": {"route": route},
        }
