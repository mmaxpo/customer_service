from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable

from app.runtime.capabilities.execution.outcomes import (
    CapabilityExecutionOutcome,
)


CAPABILITY_EXECUTION_COMPLETED_EVENT = (
    "runtime.capability.execution.completed"
)
CAPABILITY_EXECUTION_EVENT_SOURCE = "runtime.capabilities"


@runtime_checkable
class CapabilityOutcomeReporter(Protocol):
    async def report(
        self,
        outcome: CapabilityExecutionOutcome,
    ) -> None:
        ...


class NullCapabilityOutcomeReporter:
    """
    Production-safe default that performs no persistence or external I/O.
    """

    async def report(
        self,
        outcome: CapabilityExecutionOutcome,
    ) -> None:
        return None


class InMemoryCapabilityOutcomeReporter:
    """
    Test and development reporter retaining outcomes in invocation order.
    """

    def __init__(self) -> None:
        self._outcomes: list[CapabilityExecutionOutcome] = []

    async def report(
        self,
        outcome: CapabilityExecutionOutcome,
    ) -> None:
        self._outcomes.append(outcome)

    @property
    def outcomes(self) -> list[CapabilityExecutionOutcome]:
        return list(self._outcomes)

    def clear(self) -> None:
        self._outcomes.clear()


class CompositeCapabilityOutcomeReporter:
    """
    Fan out one outcome to multiple independent reporters.

    Each reporter failure is isolated so an observability adapter cannot block
    another adapter. The CapabilityInvoker also retains its outer best-effort
    guard.
    """

    def __init__(
        self,
        reporters: Iterable[CapabilityOutcomeReporter],
    ) -> None:
        self._reporters = tuple(reporters)

    @property
    def reporters(self) -> tuple[CapabilityOutcomeReporter, ...]:
        return self._reporters

    async def report(
        self,
        outcome: CapabilityExecutionOutcome,
    ) -> None:
        for reporter in self._reporters:
            try:
                await reporter.report(outcome)
            except Exception:
                continue


class PlatformCapabilityOutcomeReporter:
    """
    Publish capability outcomes through an explicitly supplied platform-event
    publisher.

    This reporter intentionally does not construct a publisher from the
    capability runtime database session. PlatformEventStore currently commits
    its session; automatic reuse of a business transaction session could commit
    unrelated capability work.

    The caller must supply a publisher backed by an independently managed
    session or another transactionally safe publisher implementation.
    """

    def __init__(
        self,
        *,
        publisher: Any,
        dispatch: bool = False,
    ) -> None:
        if publisher is None:
            raise ValueError("publisher is required")

        self.publisher = publisher
        self.dispatch = bool(dispatch)

    async def report(
        self,
        outcome: CapabilityExecutionOutcome,
    ) -> None:
        payload = self._build_payload(outcome)
        meta = self._build_meta(outcome)

        await self.publisher.publish(
            event_type=CAPABILITY_EXECUTION_COMPLETED_EVENT,
            source=CAPABILITY_EXECUTION_EVENT_SOURCE,
            payload=payload,
            meta=meta,
            user_id=outcome.user_id,
            dispatch=self.dispatch,
        )

    @staticmethod
    def _build_payload(
        outcome: CapabilityExecutionOutcome,
    ) -> dict[str, Any]:
        return {
            "requested_capability_id": (
                outcome.requested_capability_id
            ),
            "resolved_capability_id": (
                outcome.resolved_capability_id
            ),
            "status": outcome.status.value,
            "ok": outcome.ok,
            "selected_provider_id": (
                outcome.selected_provider_id
            ),
            "provider_ref": outcome.provider_ref,
            "fallback_used": outcome.fallback_used,
            "attempts": [
                attempt.model_dump(mode="json")
                for attempt in outcome.attempts
            ],
            "error_code": outcome.error_code,
            "error_message": outcome.error_message,
            "failure_kind": outcome.failure_kind,
            "exception_type": outcome.exception_type,
            "duration_ms": outcome.duration_ms,
            "verification_context": (
                outcome.verification_context
            ),
            "created_at_ts": outcome.created_at_ts,
        }

    @staticmethod
    def _build_meta(
        outcome: CapabilityExecutionOutcome,
    ) -> dict[str, Any]:
        invocation_meta = dict(
            outcome.invocation_metadata or {}
        )

        return {
            "correlation_id": outcome.correlation_id,
            "tenant_id": outcome.tenant_id,
            "workflow_run_id": invocation_meta.get(
                "workflow_run_id"
            ),
            "planner_session_id": invocation_meta.get(
                "planner_session_id"
            ),
            "thread_id": invocation_meta.get("thread_id"),
            "invocation_metadata": invocation_meta,
        }


__all__ = [
    "CAPABILITY_EXECUTION_COMPLETED_EVENT",
    "CAPABILITY_EXECUTION_EVENT_SOURCE",
    "CapabilityOutcomeReporter",
    "CompositeCapabilityOutcomeReporter",
    "InMemoryCapabilityOutcomeReporter",
    "NullCapabilityOutcomeReporter",
    "PlatformCapabilityOutcomeReporter",
]
