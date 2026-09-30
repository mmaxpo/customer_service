from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from app.runtime.nodes.types import NodeRunResult, RuntimeContext
from app.runtime.nodes.configs import AgentLangGraphConfig


class AgentLangGraphNode:
    """
    Agent node backed by LangGraph.

    This node delegates reasoning/tool-use to ctx.app.state.knowledge_agent while
    your own workflow engine remains the outer orchestration layer.

    Reads input from:
        - state.last
        - state.vars[input_key]

    Writes:
        - state.last = answer
        - optionally state.vars[save_as] = answer

    Example:
        User message -> agent.langgraph -> answer
    """

    async def run(
        self, ctx: RuntimeContext, state: Dict[str, Any], config: AgentLangGraphConfig
    ) -> NodeRunResult:
        vars_ = state.get("vars") or {}
        last = state.get("last")

        if config.input_from == "vars":
            user_text = str(vars_.get(config.input_key, "")).strip()
        else:
            user_text = str(last or "").strip()

        agent = ctx.app.state.knowledge_agent

        msgs = []
        if config.system_prompt:
            msgs.append(SystemMessage(content=config.system_prompt))
        msgs.append(HumanMessage(content=user_text))

        out = await agent.ainvoke(
            {"messages": msgs},
            config={
                "configurable": {"user_id": ctx.user_id, "thread_id": ctx.thread_id}
            },
        )

        answer = out["messages"][-1].content

        patch: Dict[str, Any] = {"last": answer}

        if config.save_as:
            patch["vars"] = {config.save_as: answer}

        return {"patch": patch, "output": answer, "meta": {}}
