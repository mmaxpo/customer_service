from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.agents_runtime.state.schemas import AgentState


def _openai_item_to_jsonable(value: Any) -> dict[str, Any] | None:
    item_type = getattr(value, "type", None)

    if item_type == "function_call":
        return {
            "type": "function_call",
            "name": getattr(value, "name"),
            "arguments": getattr(value, "arguments"),
            "call_id": getattr(value, "call_id"),
        }

    if item_type == "function_call_output":
        return {
            "type": "function_call_output",
            "call_id": getattr(value, "call_id"),
            "output": getattr(value, "output"),
        }

    content = getattr(value, "content", None)
    role = getattr(value, "role", None)

    if content is not None and role is not None:
        return {
            "role": role,
            "content": content,
        }

    return None


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value

    if isinstance(value, Enum):
        return value.value

    sdk_item = _openai_item_to_jsonable(value)
    if sdk_item is not None:
        return _to_jsonable(sdk_item)

    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}

    if isinstance(value, list | tuple):
        return [_to_jsonable(v) for v in value]

    if is_dataclass(value):
        return _to_jsonable(asdict(value))

    if isinstance(value, BaseModel):
        return _to_jsonable(value.model_dump(mode="json"))

    return str(value)


def dump_agent_state(state: AgentState) -> dict[str, Any]:
    return {
        "agent_run_id": state.agent_run_id,
        "status": _to_jsonable(state.status),
        "input_items": _to_jsonable(state.input_items),
        "steps": state.steps,
        "final_output": state.final_output,
        "errors": _to_jsonable(state.errors),
        "pending_approval": _to_jsonable(state.pending_approval),
        "vars": _to_jsonable(state.vars),
        "meta": _to_jsonable(state.meta),
    }


def load_agent_state(data: dict[str, Any]) -> AgentState:
    return AgentState.model_validate(data)
