from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException

from app.runtime.capabilities.execution.contracts import (
    CapabilityExecutionContext,
)
from app.runtime.capabilities.execution.registry import (
    CapabilityExecutorRegistry,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
    CapabilityInvocationStatus,
    CapabilityResult,
)
from app.runtime.capabilities.registry import (
    CapabilityResolutionResult,
    CapabilityRisk,
    CapabilitySystem,
)


class CapabilityExecutionRunner:
    """Execute resolved providers and construct stable runtime results."""

    def __init__(
        self,
        *,
        services: Any,
        system: CapabilitySystem,
        executor_registry: CapabilityExecutorRegistry,
    ) -> None:
        self.services = services
        self.system = system
        self.executor_registry = executor_registry

    async def _invoke_provider(
        self,
        *,
        invocation: CapabilityInvocation,
        resolution: CapabilityResolutionResult,
    ) -> Any:
        provider_ref = resolution.provider_ref

        if not provider_ref:
            raise ValueError(
                "No runtime provider executor registered for "
                f"{resolution.capability_id}"
            )

        return await self.executor_registry.execute(
            provider_ref,
            CapabilityExecutionContext(
                invocation=invocation,
                resolution=resolution,
                services=self.services,
            ),
        )

    def _can_fallback(
        self,
        *,
        resolution: CapabilityResolutionResult,
        failure_fallback_candidate: bool,
    ) -> bool:
        if not failure_fallback_candidate:
            return False

        if resolution.risk != CapabilityRisk.SAFE:
            return False

        if resolution.requires_approval:
            return False

        provider_id = resolution.selected_provider_id

        if not provider_id:
            return False

        if not self.system.providers.has(provider_id):
            return False

        provider = self.system.providers.get(provider_id)

        if not provider.supports_fallback:
            return False

        capability = self.system.capabilities.get_capability(resolution.capability_id)

        if capability.risk != CapabilityRisk.SAFE:
            return False

        return True

    @staticmethod
    def _execution_attempt(
        *,
        resolution: CapabilityResolutionResult,
        outcome: str,
        duration_ms: float,
        error_code: str | None = None,
        error_message: str | None = None,
        failure_kind: str | None = None,
        exception_type: str | None = None,
        fallback_allowed: bool = False,
    ) -> dict[str, Any]:
        return {
            "provider_id": resolution.selected_provider_id,
            "provider_ref": resolution.provider_ref,
            "capability_id": resolution.capability_id,
            "outcome": outcome,
            "duration_ms": duration_ms,
            "error_code": error_code,
            "error_message": error_message,
            "failure_kind": failure_kind,
            "exception_type": exception_type,
            "fallback_allowed": fallback_allowed,
            "health_probe": bool(
                (
                    (resolution.metadata.get("provider_health") or {}).get(
                        "health_probe"
                    )
                    or {}
                ).get("acquired", False)
            ),
            "health_probe_lease_token": (
                (
                    (resolution.metadata.get("provider_health") or {}).get(
                        "health_probe"
                    )
                    or {}
                ).get("lease_token")
            ),
        }

    def _integration_error_result(
        self,
        *,
        invocation: CapabilityInvocation,
        resolution: CapabilityResolutionResult,
        started: float,
        attempts: list[dict[str, Any]],
        error_code: str,
        error_message: str,
        failure_kind: str,
        exception_type: str,
        fallback_resolution: CapabilityResolutionResult | None = None,
    ) -> CapabilityResult:
        extra: dict[str, Any] = {
            "execution_attempts": attempts,
            "fallback_used": len(attempts) > 1,
            "failure_kind": failure_kind,
            "exception_type": exception_type,
        }

        if fallback_resolution is not None:
            extra["fallback_resolution"] = fallback_resolution.model_dump(mode="json")

        return CapabilityResult(
            status=CapabilityInvocationStatus.ERROR,
            capability_id=invocation.capability_id,
            error_code=error_code,
            error_message=error_message,
            duration_ms=self._duration_ms(started),
            metadata=self._result_metadata(
                invocation=invocation,
                resolution=resolution,
                extra=extra,
            ),
        )

    def _resolution_error_result(
        self,
        *,
        invocation: CapabilityInvocation,
        resolution: CapabilityResolutionResult,
        started: float,
        attempts: list[dict[str, Any]] | None = None,
    ) -> CapabilityResult:
        diagnostics = resolution.metadata.get("diagnostics") or {}
        status = diagnostics.get("status")

        if status == "capability_not_registered":
            error_code = "unknown_capability"
            error_message = (
                f"No capability resolver registered for {invocation.capability_id}"
            )
        elif status == "missing_inputs":
            if "order_ref" in resolution.missing_inputs:
                error_code = "missing_order_ref"
                error_message = (
                    f"Capability {invocation.capability_id} requires payload.order_ref"
                )
            else:
                error_code = "missing_required_input"
                missing = ", ".join(
                    f"payload.{key}" for key in resolution.missing_inputs
                )
                error_message = (
                    f"Capability {invocation.capability_id} requires {missing}"
                )
        elif status == "no_enabled_binding":
            error_code = "no_capability_provider_available"
            error_message = resolution.explanation
        else:
            error_code = "capability_resolution_failed"
            error_message = (
                resolution.explanation
                or f"Capability {invocation.capability_id} could not be resolved"
            )

        return CapabilityResult(
            status=CapabilityInvocationStatus.ERROR,
            capability_id=invocation.capability_id,
            error_code=error_code,
            error_message=error_message,
            duration_ms=self._duration_ms(started),
            metadata=self._result_metadata(
                invocation=invocation,
                resolution=resolution,
                extra={
                    "execution_attempts": attempts or [],
                    "fallback_used": False,
                },
            ),
        )

    def _result_metadata(
        self,
        *,
        invocation: CapabilityInvocation,
        resolution: CapabilityResolutionResult | None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "correlation_id": invocation.correlation_id,
            **invocation.metadata,
        }

        if resolution is not None:
            metadata.update(
                {
                    "resolved_capability_id": resolution.capability_id,
                    "selected_provider_id": (resolution.selected_provider_id),
                    "provider_ref": resolution.provider_ref,
                    "runtime_node_type": resolution.runtime_node_type,
                    "requires_approval": resolution.requires_approval,
                    "risk": resolution.risk.value,
                    "resolution": resolution.model_dump(mode="json"),
                }
            )

        if extra:
            metadata.update(extra)

        return metadata

    @staticmethod
    def _duration_ms(started: float) -> float:
        return (time.perf_counter() - started) * 1000

    @staticmethod
    def _http_error_code(exc: HTTPException) -> str:
        detail = str(exc.detail or "").lower()

        if exc.status_code == 404 and "shopify connection" in detail:
            return "shopify_connection_not_found"

        if exc.status_code == 404 and "order" in detail:
            return "order_not_found"

        if exc.status_code == 401:
            return "capability_unauthorized"

        if exc.status_code == 403:
            return "capability_forbidden"

        return f"http_{exc.status_code}"

    @staticmethod
    def _value_error_code(message: str) -> str:
        lowered = message.lower()

        if "no runtime provider executor registered" in lowered:
            return "provider_executor_not_registered"

        if "no capability resolver registered" in lowered:
            return "unknown_capability"

        if "requires payload.order_ref" in lowered:
            return "missing_order_ref"

        if "requires user_id" in lowered:
            return "missing_user_id"

        if "requires services.business.shopify" in lowered:
            return "missing_shopify_service"

        return "capability_invocation_error"
