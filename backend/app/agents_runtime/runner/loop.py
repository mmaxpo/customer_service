from __future__ import annotations

import json
from typing import Any

from app.agents_runtime.events import AgentEventType, EventRecorder
from app.agents_runtime.runner.context import AgentRuntimeContext
from app.agents_runtime.state import AgentState, AgentStatus, PendingApproval
from app.agents_runtime.tools import ToolExecutor, ToolRegistry
from app.agents_runtime.usage import UsageTracker
from app.agents_runtime.usage.budget import UsageBudget
from app.core.providers.llm import AgentLLMClientProtocol as LLMClientProtocol


async def _llm_respond(
    llm: LLMClientProtocol,
    *,
    input_items: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    has_tools: bool,
    max_output_tokens: int | None = None,
    reasoning_effort: str | None = None,
    verbosity: str | None = None,
):
    kwargs: dict[str, Any] = {
        "input_items": input_items,
        "tools": tools,
    }
    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort

    if verbosity:
        kwargs["verbosity"] = verbosity

    if max_output_tokens is not None and not has_tools:
        kwargs["max_output_tokens"] = max_output_tokens

    try:
        return await llm.respond(**kwargs)
    except TypeError as exc:
        unsupported_keys = ["max_output_tokens", "reasoning_effort", "verbosity"]

        if not any(key in str(exc) for key in unsupported_keys):
            raise

        for key in unsupported_keys:
            kwargs.pop(key, None)

        return await llm.respond(**kwargs)


def _response_output_items(response: Any) -> list[Any]:
    return list(getattr(response, "output", []) or [])


def _response_output_text(response: Any) -> str:
    return str(getattr(response, "output_text", "") or "")


def _is_function_call(item: Any) -> bool:
    return getattr(item, "type", None) == "function_call"


def _item_name(item: Any) -> str:
    return str(getattr(item, "name"))


def _item_arguments(item: Any) -> dict[str, Any]:
    raw = getattr(item, "arguments", "{}") or "{}"
    return json.loads(raw)


def _item_call_id(item: Any) -> str | None:
    return getattr(item, "call_id", None)


def _normalize_output_item(item: Any) -> dict[str, Any]:
    item_type = getattr(item, "type", None)

    if item_type == "function_call":
        return {
            "type": "function_call",
            "name": getattr(item, "name"),
            "arguments": getattr(item, "arguments"),
            "call_id": getattr(item, "call_id"),
        }

    if item_type == "function_call_output":
        return {
            "type": "function_call_output",
            "call_id": getattr(item, "call_id"),
            "output": getattr(item, "output"),
        }

    role = getattr(item, "role", None)
    content = getattr(item, "content", None)

    if role is not None and content is not None:
        return {
            "role": role,
            "content": content,
        }

    return {
        "role": "assistant",
        "content": str(getattr(item, "content", "") or ""),
    }


def _normalize_output_items(items: list[Any]) -> list[dict[str, Any]]:
    return [_normalize_output_item(item) for item in items]


def _check_usage_budget(
    *,
    usage_tracker,
    budget: UsageBudget | None,
) -> None:
    if usage_tracker and budget:
        budget.check(usage_tracker.usage)


async def run_tool_agent_loop(
    *,
    llm: LLMClientProtocol,
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
    state: AgentState,
    context: AgentRuntimeContext,
    recorder: EventRecorder,
    system_prompt: str,
    user_input: str,
    tool_names: list[str] | None = None,
    max_steps: int = 8,
    usage_tracker: UsageTracker | None = None,
    usage_budget: UsageBudget | None = None,
    max_output_tokens: int | None = None,
    reasoning_effort: str | None = None,
    verbosity: str | None = None,
) -> AgentState:
    if state.status == AgentStatus.CREATED:
        state.mark_running()

    recorder.emit(
        agent_run_id=context.agent_run_id,
        event_type=AgentEventType.RUN_STARTED,
        step=state.steps,
        payload={"input": user_input},
    )

    state.input_items = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_input,
        },
    ]

    try:
        while state.steps < max_steps:
            state.steps += 1

            recorder.emit(
                agent_run_id=context.agent_run_id,
                event_type=AgentEventType.LLM_CALL_STARTED,
                step=state.steps,
            )

            response = await _llm_respond(
                llm,
                input_items=state.input_items,
                tools=tool_registry.to_openai_tools(tool_names),
                has_tools=bool(tool_names),
                max_output_tokens=max_output_tokens,
                reasoning_effort=reasoning_effort,
                verbosity=verbosity,
            )

            recorder.emit(
                agent_run_id=context.agent_run_id,
                event_type=AgentEventType.LLM_CALL_FINISHED,
                step=state.steps,
                payload={
                    "output_text": _response_output_text(response),
                    "usage": (
                        usage_tracker.record_llm_response(response).model_dump()
                        if usage_tracker
                        else None
                    ),
                    "run_usage": (
                        usage_tracker.usage.model_dump() if usage_tracker else None
                    ),
                },
            )

            _check_usage_budget(
                usage_tracker=usage_tracker,
                budget=usage_budget,
            )

            output_items = _response_output_items(response)
            state.input_items += _normalize_output_items(output_items)

            handled_tool_call = False

            for item in output_items:
                if not _is_function_call(item):
                    continue

                handled_tool_call = True
                tool_name = _item_name(item)
                args = _item_arguments(item)
                call_id = _item_call_id(item)

                recorder.emit(
                    agent_run_id=context.agent_run_id,
                    event_type=AgentEventType.TOOL_CALL_STARTED,
                    step=state.steps,
                    payload={
                        "tool_name": tool_name,
                        "arguments": args,
                    },
                )

                tool = tool_registry.get(tool_name)

                if tool.requires_approval:
                    state.mark_paused(
                        PendingApproval(
                            tool_name=tool_name,
                            arguments=args,
                            call_id=call_id,
                        )
                    )

                    recorder.emit(
                        agent_run_id=context.agent_run_id,
                        event_type=AgentEventType.APPROVAL_REQUIRED,
                        step=state.steps,
                        payload={
                            "tool_name": tool_name,
                            "arguments": args,
                        },
                    )

                    return state

                if usage_tracker:
                    usage_tracker.record_tool_call()
                _check_usage_budget(
                    usage_tracker=usage_tracker,
                    budget=usage_budget,
                )
                result = await tool_executor.execute(tool_name, args)

                recorder.emit(
                    agent_run_id=context.agent_run_id,
                    event_type=AgentEventType.TOOL_CALL_FINISHED,
                    step=state.steps,
                    payload={
                        "tool_name": tool_name,
                        "result": result,
                    },
                )

                state.input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result),
                    }
                )

                break

            if handled_tool_call:
                continue

            final_output = _response_output_text(response).strip()

            if not final_output:
                state.mark_failed("LLM returned empty output with no tool call.")
                recorder.emit(
                    agent_run_id=context.agent_run_id,
                    event_type=AgentEventType.RUN_FAILED,
                    step=state.steps,
                    payload={"error": "LLM returned empty output with no tool call."},
                )
                return state

            state.mark_completed(final_output)

            recorder.emit(
                agent_run_id=context.agent_run_id,
                event_type=AgentEventType.RUN_COMPLETED,
                step=state.steps,
                payload={"final_output": final_output},
            )

            return state

        state.mark_failed("Max steps reached.")

        recorder.emit(
            agent_run_id=context.agent_run_id,
            event_type=AgentEventType.RUN_FAILED,
            step=state.steps,
            payload={"error": "Max steps reached."},
        )

        return state

    except Exception as exc:
        state.mark_failed(str(exc))

        recorder.emit(
            agent_run_id=context.agent_run_id,
            event_type=AgentEventType.RUN_FAILED,
            step=state.steps,
            payload={"error": str(exc)},
        )

        return state


async def continue_after_approval(
    *,
    llm: LLMClientProtocol,
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
    state: AgentState,
    context: AgentRuntimeContext,
    recorder: EventRecorder,
    approved: bool,
    rejection_reason: str | None = None,
    tool_names: list[str] | None = None,
    max_steps: int = 8,
    usage_tracker: UsageTracker | None = None,
    usage_budget: UsageBudget | None = None,
    max_output_tokens: int | None = None,
    reasoning_effort: str | None = None,
    verbosity: str | None = None,
) -> AgentState:
    if state.status != AgentStatus.PAUSED or not state.pending_approval:
        state.mark_failed("No pending approval to resume.")
        return state

    approval = state.pending_approval

    if not approved:
        message = (
            rejection_reason
            or "Request was rejected by human reviewer. No action was taken."
        )

        state.resume_from_pause()
        state.mark_completed(message)

        return state

    recorder.emit(
        agent_run_id=context.agent_run_id,
        event_type=AgentEventType.APPROVAL_GRANTED,
        step=state.steps,
        payload={
            "tool_name": approval.tool_name,
            "arguments": approval.arguments,
        },
    )

    state.resume_from_pause()

    if usage_tracker:
        usage_tracker.record_tool_call()
    _check_usage_budget(
        usage_tracker=usage_tracker,
        budget=usage_budget,
    )
    result = await tool_executor.execute(
        approval.tool_name,
        approval.arguments,
    )

    recorder.emit(
        agent_run_id=context.agent_run_id,
        event_type=AgentEventType.TOOL_CALL_FINISHED,
        step=state.steps,
        payload={
            "tool_name": approval.tool_name,
            "result": result,
        },
    )

    state.input_items.append(
        {
            "type": "function_call_output",
            "call_id": approval.call_id,
            "output": json.dumps(result),
        }
    )

    try:
        while state.steps < max_steps:
            state.steps += 1

            recorder.emit(
                agent_run_id=context.agent_run_id,
                event_type=AgentEventType.LLM_CALL_STARTED,
                step=state.steps,
            )

            response = await _llm_respond(
                llm,
                input_items=state.input_items,
                tools=tool_registry.to_openai_tools(tool_names),
                has_tools=bool(tool_names),
                max_output_tokens=max_output_tokens,
                reasoning_effort=reasoning_effort,
                verbosity=verbosity,
            )

            recorder.emit(
                agent_run_id=context.agent_run_id,
                event_type=AgentEventType.LLM_CALL_FINISHED,
                step=state.steps,
                payload={
                    "output_text": _response_output_text(response),
                    "usage": (
                        usage_tracker.record_llm_response(response).model_dump()
                        if usage_tracker
                        else None
                    ),
                    "run_usage": (
                        usage_tracker.usage.model_dump() if usage_tracker else None
                    ),
                },
            )

            _check_usage_budget(
                usage_tracker=usage_tracker,
                budget=usage_budget,
            )

            output_items = _response_output_items(response)
            state.input_items += _normalize_output_items(output_items)

            handled_tool_call = False

            for item in output_items:
                if not _is_function_call(item):
                    continue

                handled_tool_call = True
                tool_name = _item_name(item)
                args = _item_arguments(item)
                call_id = _item_call_id(item)

                recorder.emit(
                    agent_run_id=context.agent_run_id,
                    event_type=AgentEventType.TOOL_CALL_STARTED,
                    step=state.steps,
                    payload={
                        "tool_name": tool_name,
                        "arguments": args,
                    },
                )

                tool = tool_registry.get(tool_name)

                if tool.requires_approval:
                    state.mark_paused(
                        PendingApproval(
                            tool_name=tool_name,
                            arguments=args,
                            call_id=call_id,
                        )
                    )

                    recorder.emit(
                        agent_run_id=context.agent_run_id,
                        event_type=AgentEventType.APPROVAL_REQUIRED,
                        step=state.steps,
                        payload={
                            "tool_name": tool_name,
                            "arguments": args,
                        },
                    )

                    return state

                if usage_tracker:
                    usage_tracker.record_tool_call()
                _check_usage_budget(
                    usage_tracker=usage_tracker,
                    budget=usage_budget,
                )
                result = await tool_executor.execute(tool_name, args)

                recorder.emit(
                    agent_run_id=context.agent_run_id,
                    event_type=AgentEventType.TOOL_CALL_FINISHED,
                    step=state.steps,
                    payload={
                        "tool_name": tool_name,
                        "result": result,
                    },
                )

                state.input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result),
                    }
                )

                break

            if handled_tool_call:
                continue

            final_output = _response_output_text(response).strip()

            if not final_output:
                state.mark_failed("LLM returned empty output with no tool call.")
                recorder.emit(
                    agent_run_id=context.agent_run_id,
                    event_type=AgentEventType.RUN_FAILED,
                    step=state.steps,
                    payload={"error": "LLM returned empty output with no tool call."},
                )
                return state

            state.mark_completed(final_output)

            recorder.emit(
                agent_run_id=context.agent_run_id,
                event_type=AgentEventType.RUN_COMPLETED,
                step=state.steps,
                payload={"final_output": final_output},
            )

            return state

        state.mark_failed("Max steps reached.")

        recorder.emit(
            agent_run_id=context.agent_run_id,
            event_type=AgentEventType.RUN_FAILED,
            step=state.steps,
            payload={"error": "Max steps reached."},
        )

        return state

    except Exception as exc:
        state.mark_failed(str(exc))

        recorder.emit(
            agent_run_id=context.agent_run_id,
            event_type=AgentEventType.RUN_FAILED,
            step=state.steps,
            payload={"error": str(exc)},
        )

        return state
