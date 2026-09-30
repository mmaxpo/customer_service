from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ContextExtractConfig(BaseModel):
    """
    Copy a value from runtime context into durable workflow state.

    Supported sources:
    - extras: ctx.extras
    - event: ctx.extras["event"]
    - event_payload: ctx.extras["event"]["payload"]

    Nested paths use dot notation, for example:
        session_id
        widget.workflow_template_id
    """

    node_type: Literal["context.extract"] = "context.extract"

    source: Literal["extras", "event", "event_payload"] = Field(
        default="event_payload"
    )
    path: str = Field(min_length=1)
    save_as: str = Field(min_length=1)

    required: bool = True
    default: Any = None
    update_last: bool = False


class ContextExtractNode:
    async def run(
        self,
        ctx,
        state: dict[str, Any],
        config: ContextExtractConfig,
    ) -> dict[str, Any]:
        extras = getattr(ctx, "extras", None) or {}

        if config.source == "extras":
            source: Any = extras
        elif config.source == "event":
            source = extras.get("event") or {}
        else:
            event = extras.get("event") or {}
            source = (
                event.get("payload") or {}
                if isinstance(event, dict)
                else {}
            )

        value, found = _get_by_path(source, config.path)

        if not found:
            if config.required:
                raise ValueError(
                    "context.extract could not resolve "
                    f"{config.source}.{config.path}"
                )

            value = config.default

        patch: dict[str, Any] = {
            "vars": {
                config.save_as: value,
            }
        }

        if config.update_last:
            patch["last"] = value

        return {
            "output": value,
            "update_last": config.update_last,
            "patch": patch,
            "meta": {
                "source": config.source,
                "path": config.path,
                "save_as": config.save_as,
                "found": found,
            },
        }


def _get_by_path(source: Any, path: str) -> tuple[Any, bool]:
    current = source

    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue

        if isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return None, False

            if 0 <= index < len(current):
                current = current[index]
                continue

        return None, False

    return current, True
