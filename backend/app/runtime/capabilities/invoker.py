from __future__ import annotations
from typing import Any
from app.runtime.capabilities.execution import (
    CapabilityOutcomeReporter,
    NullCapabilityOutcomeReporter,
    build_capability_execution_outcome,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
    CapabilityResult,
)

from app.runtime.capabilities.resolver import CapabilityResolver


class CapabilityInvoker:
    """
    Public capability invocation lifecycle.

    The resolver owns semantic resolution and execution. The invoker creates
    exactly one final CapabilityExecutionOutcome and reports it through an
    injected reporter.
    """

    def __init__(
        self,
        *,
        resolver: CapabilityResolver,
        outcome_reporter: CapabilityOutcomeReporter | None = None,
    ):
        self.resolver = resolver
        self.outcome_reporter = outcome_reporter or NullCapabilityOutcomeReporter()

    async def resolve(
        self,
        invocation: CapabilityInvocation,
    ) -> CapabilityResult:
        result = await self.resolver.resolve(invocation)

        tenant_id = getattr(
            getattr(self.resolver.services, "identity", None),
            "tenant_id",
            None,
        )

        outcome = build_capability_execution_outcome(
            invocation=invocation,
            result=result,
            tenant_id=tenant_id,
        )

        completion = await self._complete_health_probe(outcome)

        if completion is not None:
            result.metadata = {
                **dict(result.metadata or {}),
                "health_probe_completion": completion,
            }
            outcome.result_metadata = {
                **dict(outcome.result_metadata or {}),
                "health_probe_completion": completion,
            }

        result.metadata = {
            **dict(result.metadata or {}),
            "execution_outcome": outcome.model_dump(mode="json"),
        }

        await self._report_outcome(outcome)
        return result

    async def _complete_health_probe(
        self,
        outcome,
    ) -> dict[str, Any] | None:
        """
        Complete the single controlled probe attempt, if present.

        Completion is observationally isolated. Database or coordinator
        failures cannot alter the caller-facing capability result.
        """

        probe_attempt = next(
            (
                item
                for item in outcome.attempts
                if item.health_probe and item.health_probe_lease_token
            ),
            None,
        )

        if probe_attempt is None:
            return None

        user_id = outcome.user_id or getattr(
            getattr(
                self.resolver.services,
                "identity",
                None,
            ),
            "user_id",
            None,
        )

        tenant_id = outcome.tenant_id or getattr(
            getattr(
                self.resolver.services,
                "identity",
                None,
            ),
            "tenant_id",
            None,
        )

        try:
            completion = await (
                self.resolver.provider_health_probe_coordinator.complete_probe(
                    user_id=(str(user_id) if user_id is not None else None),
                    tenant_id=(str(tenant_id) if tenant_id is not None else None),
                    capability_id=(
                        probe_attempt.capability_id
                        or outcome.resolved_capability_id
                        or outcome.requested_capability_id
                    ),
                    provider_id=(probe_attempt.provider_id or ""),
                    provider_ref=(probe_attempt.provider_ref),
                    lease_token=(probe_attempt.health_probe_lease_token),
                    succeeded=(probe_attempt.outcome == "success"),
                    failure_cooldown_seconds=(
                        self.resolver.provider_health_probe_failure_cooldown_seconds
                    ),
                    failure_kind=(probe_attempt.failure_kind),
                    error_code=probe_attempt.error_code,
                    error_message=(probe_attempt.error_message),
                    metadata={
                        "correlation_id": (outcome.correlation_id),
                        "fallback_used": (outcome.fallback_used),
                    },
                )
            )
        except Exception as exc:
            return {
                "completed": False,
                "reason": ("probe_completion_failed_open"),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }

        return completion.model_dump(mode="json")

    async def _report_outcome(
        self,
        outcome,
    ) -> None:
        """
        Reporting is observational and must never change invocation success.

        Persistence/event adapters may fail independently. Such failures are
        intentionally isolated from the capability execution contract.
        """

        try:
            await self.outcome_reporter.report(outcome)
        except Exception:
            return None

    async def invoke(
        self,
        capability_id: str,
        *,
        payload: dict[str, Any] | None = None,
        user_id: Any = None,
    ) -> Any:
        result = await self.resolve(
            CapabilityInvocation(
                capability_id=capability_id,
                inputs=payload or {},
                user_id=user_id,
            )
        )

        if not result.ok:
            raise ValueError(result.error_message or "Capability invocation failed")

        return result.output
