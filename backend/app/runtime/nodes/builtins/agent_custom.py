from __future__ import annotations

from typing import Any

from app.agents_runtime.config import AgentCustomConfig
from app.agents_runtime.runner import AgentRunner, AgentRuntimeContext
from app.agents_runtime.state import dump_agent_state, load_agent_state
from app.agents_runtime.tools import build_builtin_tool_registry
from app.core.token_control.token_budget import resolve_max_output_tokens


def _truncate_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + "\n...[truncated]"


def _read_input(config: AgentCustomConfig, state: dict[str, Any]) -> str:
    vars_ = state.get("vars") or {}

    role = getattr(config, "role", "worker")
    is_final = role in {"final", "final_writer"}

    context_keys = getattr(config, "context_keys", None) or []
    if context_keys:
        parts = []

        for key in context_keys:
            if key in vars_:
                parts.append(f"{key}:\n{vars_[key]}")

        if parts:
            return "\n\n---\n\n".join(parts)

    if config.input_from == "vars":
        value = vars_.get(config.input_key, "")

        if is_final:
            value = (
                vars_.get("decision_agent_result")
                or vars_.get(config.input_key)
                or state.get("last")
                or ""
            )

        return str(value)

    return str(state.get("last") or vars_.get("input", ""))


def _get_llm_from_ctx(ctx):
    tools = getattr(ctx, "tools", None)

    if tools is not None and hasattr(tools, "agent_llm"):
        llm = tools.agent_llm
        if hasattr(llm, "respond"):
            return llm

    if tools is not None and hasattr(tools, "llm"):
        llm = tools.llm
        if hasattr(llm, "respond"):
            return llm

    app = getattr(ctx, "app", None)

    if app is not None and hasattr(app.state, "agent_llm"):
        llm = app.state.agent_llm
        if hasattr(llm, "respond"):
            return llm

    raise RuntimeError(
        "No agent LLM client found. Expected async respond(...) client "
        "at ctx.tools.agent_llm, ctx.tools.llm, or app.state.agent_llm."
    )


def _agent_snapshot_key(config: AgentCustomConfig) -> str:
    return f"__agent_custom_snapshot__:{config.save_as or 'agent_result'}"


def _read_resume_input(ctx) -> dict[str, Any]:
    extras = getattr(ctx, "extras", None) or {}
    return extras.get("resume_input") or {}


def _harden_system_prompt(config: AgentCustomConfig) -> str:
    role = getattr(config, "role", "worker")
    output_mode = getattr(config, "output_mode", "text")

    base = config.system_prompt or "You are a helpful AI agent."

    rules = [
        "Be concise.",
        "Do not include internal reasoning.",
        "Do not ask for information that already exists in the provided context.",
        "Do not create long explanations unless required.",
    ]

    if role == "worker":
        rules.append("Return only facts/results from your assigned responsibility.")
    elif role == "decision":
        rules.append("Create one source-of-truth decision from the inputs.")
        rules.append(
            "Describe proposed actions as recommendations unless a real tool result confirms execution."
        )
    elif role in {"final", "final_writer"}:
        rules.append("Write one concise final response.")
        rules.append("Use only the provided decision.")
        rules.append("Do not expose internal notes.")
        rules.append(
            "Do not claim an action was executed unless the provided input or tool result explicitly confirms execution."
        )

    if output_mode == "json":
        rules.append("Return valid JSON only. No markdown.")

    return base.rstrip() + "\n\nRuntime rules:\n- " + "\n- ".join(rules)


class AgentCustomNode:
    async def run(
        self,
        ctx,
        state: dict[str, Any],
        config: AgentCustomConfig,
    ) -> dict[str, Any]:
        input_text = config.instruction or _read_input(config, state)
        input_text = _truncate_text(
            input_text, getattr(config, "max_output_chars", 1200) * 3
        )

        tool_registry = build_builtin_tool_registry(
            tools=getattr(ctx, "tools", None),
            user_id=getattr(ctx, "user_id", None),
        )
        snapshot_key = _agent_snapshot_key(config)
        vars_ = state.get("vars") or {}
        resume_input = _read_resume_input(ctx)
        snapshot = vars_.get(snapshot_key)

        user_id = getattr(ctx, "user_id", None)
        thread_id = getattr(ctx, "thread_id", None)
        workflow_run_id = getattr(ctx, "workflow_run_id", None)

        agent_context = AgentRuntimeContext(
            user_id=str(user_id) if user_id is not None else None,
            workflow_run_id=str(workflow_run_id) if workflow_run_id else None,
            metadata={
                "workflow_node_type": "agent.custom",
                "agent_backend": config.backend,
                "agent_pattern": config.pattern,
                "thread_id": str(thread_id) if thread_id is not None else None,
            },
        )

        max_output_tokens = resolve_max_output_tokens(
            role=getattr(config, "role", None),
            requested_max_output_tokens=getattr(config, "max_output_tokens", None),
            token_budget_mode=getattr(config, "token_budget_mode", None),
        )

        runner = AgentRunner(
            llm=_get_llm_from_ctx(ctx),
            tool_registry=tool_registry,
            max_steps=config.max_steps,
            max_output_tokens=max_output_tokens,
            reasoning_effort=getattr(config, "reasoning_effort", "low"),
            verbosity=getattr(config, "verbosity", "low"),
        )

        if snapshot and resume_input:
            approved = bool(resume_input.get("approved"))
            rejection_reason = resume_input.get("reason")
            restored_state = load_agent_state(snapshot)

            agent_state, recorder = await runner.resume_after_approval(
                state=restored_state,
                approved=approved,
                rejection_reason=rejection_reason,
                tool_names=config.tools,
                context=agent_context,
            )
        else:
            agent_state, recorder = await runner.run(
                user_input=input_text,
                system_prompt=_harden_system_prompt(config),
                tool_names=config.tools,
                context=agent_context,
            )

        if str(agent_state.status) == "paused" and agent_state.pending_approval:
            approval = agent_state.pending_approval

            return {
                "status": "paused",
                "interrupt": {
                    "kind": "approval",
                    "question": (
                        f"Approve tool call `{approval.tool_name}` with arguments "
                        f"{approval.arguments}?"
                    ),
                    "expected": {"approved": "boolean"},
                    "node_type": "agent.custom",
                    "agent_run_id": agent_state.agent_run_id,
                    "workflow_run_id": workflow_run_id,
                    "snapshot_key": snapshot_key,
                    "tool_name": approval.tool_name,
                    "arguments": approval.arguments,
                    "call_id": approval.call_id,
                },
                "output": None,
                "patch": {
                    "vars": {
                        snapshot_key: dump_agent_state(agent_state),
                    }
                },
                "meta": {
                    "paused": True,
                    "agent_run_id": agent_state.agent_run_id,
                    "workflow_run_id": workflow_run_id,
                    "agent_status": agent_state.status,
                    "agent_steps": agent_state.steps,
                    "agent_pending_approval": approval.model_dump(),
                    "agent_events": [event.model_dump() for event in recorder.events],
                },
            }

        output = _truncate_text(
            agent_state.final_output or "",
            getattr(config, "max_output_chars", 1200),
        )
        agent_failed = str(agent_state.status) == "failed"

        if agent_failed and not output:
            tool_outputs = []

            for event in recorder.events:
                if event.type == "tool_call_finished":
                    result = event.payload.get("result") if event.payload else None
                    if isinstance(result, dict):
                        content = result.get("content")
                        if content:
                            tool_outputs.append(str(content))

            if tool_outputs:
                output = "\n\n".join(tool_outputs)

        if agent_failed and not output:
            raise RuntimeError(
                f"agent.custom failed with no usable output: {agent_state.errors}"
            )

        patch = {
            "vars": {
                snapshot_key: None,
            }
        }

        if config.save_as:
            patch["vars"][config.save_as] = output
            patch["vars"][f"{config.save_as}_meta"] = {
                "agent_run_id": agent_state.agent_run_id,
                "workflow_run_id": workflow_run_id,
                "agent_status": agent_state.status,
                "agent_steps": agent_state.steps,
            }

        return {
            "output": output,
            "patch": patch,
            "meta": {
                "agent_run_id": agent_state.agent_run_id,
                "workflow_run_id": workflow_run_id,
                "agent_status": agent_state.status,
                "agent_steps": agent_state.steps,
                "agent_errors": [error.model_dump() for error in agent_state.errors],
                "agent_events": [event.model_dump() for event in recorder.events],
                "agent_degraded": agent_failed and bool(output),
                "agent_pending_approval": (
                    agent_state.pending_approval.model_dump()
                    if agent_state.pending_approval
                    else None
                ),
            },
        }
