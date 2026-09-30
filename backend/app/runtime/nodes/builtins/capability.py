from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.runtime.resources import get_runtime_services
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)


class CapabilityInvokeConfig(BaseModel):
    node_type: Literal["capability.invoke"] = "capability.invoke"

    @model_validator(mode="before")
    @classmethod
    def unwrap_nested_runtime_config(cls, data):
        if isinstance(data, dict) and isinstance(data.get("config"), dict):
            merged = dict(data)
            nested = dict(merged.pop("config"))
            nested.setdefault(
                "node_type",
                merged.get("nodeType")
                or merged.get("node_type")
                or "capability.invoke",
            )
            return nested
        return data

    capability_id: str
    payload: dict[str, Any] = Field(default_factory=dict)

    input_from: Literal["config", "vars", "last"] = "config"
    input_key: str | None = None
    input_keys: tuple[str, ...] = ()

    save_as: str | None = None
    fail_on_error: bool = True


class CapabilityInvokeNode:
    async def run(
        self,
        ctx,
        state: dict[str, Any],
        config: CapabilityInvokeConfig,
    ) -> dict[str, Any]:
        services = get_runtime_services(ctx)

        if services.capabilities is None:
            raise ValueError("capability.invoke requires runtime capability invoker")

        payload = dict(config.payload or {})

        if config.input_from == "vars":
            vars_ = state.get("vars") or {}

            if config.input_key:
                value = vars_.get(config.input_key)
                payload[config.input_key] = value
            elif config.input_keys:
                for key in config.input_keys:
                    payload[key] = vars_.get(key)
            else:
                payload.update(vars_)
        elif config.input_from == "last":
            payload["input"] = state.get("last")

        result = await services.capabilities.resolve(
            CapabilityInvocation(
                capability_id=config.capability_id,
                inputs=payload,
                user_id=getattr(ctx, "user_id", None),
            )
        )

        result_data = (
            result.model_dump(mode="json")
            if hasattr(result, "model_dump")
            else dict(result)
            if isinstance(result, dict)
            else {
                "capability_id": getattr(result, "capability_id", config.capability_id),
                "ok": getattr(result, "ok", False),
                "status": getattr(
                    getattr(result, "status", None),
                    "value",
                    getattr(result, "status", None),
                ),
                "output": getattr(result, "output", None),
                "error_code": getattr(result, "error_code", None),
                "error_message": getattr(result, "error_message", None),
                "duration_ms": getattr(result, "duration_ms", None),
            }
        )

        status_value = result_data.get("status")
        ok = bool(result_data.get("ok")) or status_value == "ok"
        result_data["ok"] = ok
        if status_value is not None and hasattr(status_value, "value"):
            result_data["status"] = status_value.value
        error_message = result_data.get("error_message")
        error_code = result_data.get("error_code")

        if not ok and config.fail_on_error:
            raise ValueError(
                error_message or f"Capability {config.capability_id} failed"
            )

        output = result_data.get("output") if ok else result_data
        save_as = config.save_as or config.capability_id.replace(".", "_")

        return {
            "output": output,
            "patch": {
                "vars": {
                    save_as: output,
                    f"{save_as}_capability_result": result_data,
                },
                "last": output,
            },
            "meta": {
                "capability_id": config.capability_id,
                "ok": ok,
                "status": result_data.get("status"),
                "error_code": error_code,
                "duration_ms": result_data.get("duration_ms"),
            },
        }
