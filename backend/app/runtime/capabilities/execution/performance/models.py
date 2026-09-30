from __future__ import annotations

import time
from collections import defaultdict
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.runtime.capabilities.execution.outcomes import (
    CapabilityExecutionAttempt,
    CapabilityExecutionOutcome,
)


class CapabilityPerformanceObservationStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CapabilityPerformanceObservation(BaseModel):
    """
    Canonical evidence produced for one provider execution attempt.

    An invocation may produce multiple observations when safe provider
    fallback occurs. This keeps provider reliability evidence accurate:
    the failed primary provider and successful fallback provider are measured
    independently.
    """

    model_config = ConfigDict(extra="forbid")

    correlation_id: str
    attempt_index: int = Field(ge=0)

    requested_capability_id: str
    resolved_capability_id: str | None = None

    provider_id: str | None = None
    provider_ref: str | None = None

    status: CapabilityPerformanceObservationStatus
    succeeded: bool

    duration_ms: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    failure_kind: str | None = None
    exception_type: str | None = None

    fallback_allowed: bool = False
    fallback_used: bool = False
    final_attempt: bool = False

    health_probe: bool = False
    health_probe_lease_token: str | None = None

    user_id: str | None = None
    tenant_id: str | None = None
    workflow_run_id: str | None = None
    planner_session_id: str | None = None
    thread_id: str | None = None

    observed_at_ts: float = Field(default_factory=time.time)


class CapabilityPerformanceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str
    provider_id: str | None = None
    provider_ref: str | None = None
    tenant_id: str | None = None

    attempts: int = 0
    successes: int = 0
    failures: int = 0

    timeouts: int = 0
    unavailable: int = 0
    circuit_open: int = 0
    provider_errors: int = 0
    other_failures: int = 0

    fallback_eligible_failures: int = 0
    fallback_invocations: int = 0

    total_duration_ms: float = 0.0
    average_duration_ms: float = 0.0
    success_rate: float = 0.0

    last_error_code: str | None = None
    last_failure_kind: str | None = None
    last_observed_at_ts: float | None = None


class CapabilityPerformanceProjector:
    """
    Convert one final capability outcome into provider-attempt observations.
    """

    def project(
        self,
        outcome: CapabilityExecutionOutcome,
    ) -> list[CapabilityPerformanceObservation]:
        invocation_meta = dict(
            outcome.invocation_metadata or {}
        )

        if outcome.attempts:
            return [
                self._from_attempt(
                    outcome=outcome,
                    attempt=attempt,
                    attempt_index=index,
                    final_attempt=(
                        index == len(outcome.attempts) - 1
                    ),
                    invocation_meta=invocation_meta,
                )
                for index, attempt in enumerate(outcome.attempts)
            ]

        # Resolution failures and validation failures may not reach a provider.
        # They are intentionally excluded from provider performance evidence.
        if (
            not outcome.selected_provider_id
            and not outcome.provider_ref
        ):
            return []

        return [
            CapabilityPerformanceObservation(
                correlation_id=outcome.correlation_id,
                attempt_index=0,
                requested_capability_id=(
                    outcome.requested_capability_id
                ),
                resolved_capability_id=(
                    outcome.resolved_capability_id
                ),
                provider_id=outcome.selected_provider_id,
                provider_ref=outcome.provider_ref,
                status=(
                    CapabilityPerformanceObservationStatus.SUCCEEDED
                    if outcome.ok
                    else CapabilityPerformanceObservationStatus.FAILED
                ),
                succeeded=outcome.ok,
                duration_ms=outcome.duration_ms,
                error_code=outcome.error_code,
                error_message=outcome.error_message,
                failure_kind=outcome.failure_kind,
                exception_type=outcome.exception_type,
                fallback_used=outcome.fallback_used,
                final_attempt=True,
                user_id=outcome.user_id,
                tenant_id=outcome.tenant_id,
                workflow_run_id=self._optional_string(
                    invocation_meta.get("workflow_run_id")
                ),
                planner_session_id=self._optional_string(
                    invocation_meta.get("planner_session_id")
                ),
                thread_id=self._optional_string(
                    invocation_meta.get("thread_id")
                ),
                observed_at_ts=outcome.created_at_ts,
            )
        ]

    def _from_attempt(
        self,
        *,
        outcome: CapabilityExecutionOutcome,
        attempt: CapabilityExecutionAttempt,
        attempt_index: int,
        final_attempt: bool,
        invocation_meta: dict[str, Any],
    ) -> CapabilityPerformanceObservation:
        succeeded = attempt.outcome == "success"

        return CapabilityPerformanceObservation(
            correlation_id=outcome.correlation_id,
            attempt_index=attempt_index,
            requested_capability_id=(
                outcome.requested_capability_id
            ),
            resolved_capability_id=(
                attempt.capability_id
                or outcome.resolved_capability_id
            ),
            provider_id=attempt.provider_id,
            provider_ref=attempt.provider_ref,
            status=(
                CapabilityPerformanceObservationStatus.SUCCEEDED
                if succeeded
                else CapabilityPerformanceObservationStatus.FAILED
            ),
            succeeded=succeeded,
            duration_ms=attempt.duration_ms,
            error_code=attempt.error_code,
            error_message=attempt.error_message,
            failure_kind=attempt.failure_kind,
            exception_type=attempt.exception_type,
            fallback_allowed=attempt.fallback_allowed,
            fallback_used=outcome.fallback_used,
            final_attempt=final_attempt,
            health_probe=attempt.health_probe,
            health_probe_lease_token=(
                attempt.health_probe_lease_token
            ),
            user_id=outcome.user_id,
            tenant_id=outcome.tenant_id,
            workflow_run_id=self._optional_string(
                invocation_meta.get("workflow_run_id")
            ),
            planner_session_id=self._optional_string(
                invocation_meta.get("planner_session_id")
            ),
            thread_id=self._optional_string(
                invocation_meta.get("thread_id")
            ),
            observed_at_ts=outcome.created_at_ts,
        )

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        return normalized or None


class InMemoryCapabilityPerformanceStore:
    """
    Deterministic in-memory evidence store and aggregate projection.

    This store is intentionally observational. It does not mutate
    ProviderHealthRegistry or provider-selection policy.
    """

    def __init__(self) -> None:
        self._observations: list[
            CapabilityPerformanceObservation
        ] = []

    def record(
        self,
        observation: CapabilityPerformanceObservation,
    ) -> None:
        self._observations.append(observation)

    def record_many(
        self,
        observations: list[
            CapabilityPerformanceObservation
        ],
    ) -> None:
        self._observations.extend(observations)

    @property
    def observations(
        self,
    ) -> list[CapabilityPerformanceObservation]:
        return list(self._observations)

    def clear(self) -> None:
        self._observations.clear()

    def summarize(
        self,
        *,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        tenant_id: str | None = None,
    ) -> list[CapabilityPerformanceSummary]:
        filtered = [
            item
            for item in self._observations
            if (
                capability_id is None
                or self._capability_id(item) == capability_id
            )
            and (
                provider_id is None
                or item.provider_id == provider_id
            )
            and (
                provider_ref is None
                or item.provider_ref == provider_ref
            )
            and (
                tenant_id is None
                or item.tenant_id == tenant_id
            )
        ]

        grouped: dict[
            tuple[str, str | None, str | None, str | None],
            list[CapabilityPerformanceObservation],
        ] = defaultdict(list)

        for item in filtered:
            grouped[
                (
                    self._capability_id(item),
                    item.provider_id,
                    item.provider_ref,
                    item.tenant_id,
                )
            ].append(item)

        summaries = [
            self._summarize_group(
                capability_id=key[0],
                provider_id=key[1],
                provider_ref=key[2],
                tenant_id=key[3],
                observations=items,
            )
            for key, items in grouped.items()
        ]

        return sorted(
            summaries,
            key=lambda item: (
                item.capability_id,
                item.provider_id or "",
                item.provider_ref or "",
                item.tenant_id or "",
            ),
        )

    @staticmethod
    def _capability_id(
        observation: CapabilityPerformanceObservation,
    ) -> str:
        return (
            observation.resolved_capability_id
            or observation.requested_capability_id
        )

    @staticmethod
    def _summarize_group(
        *,
        capability_id: str,
        provider_id: str | None,
        provider_ref: str | None,
        tenant_id: str | None,
        observations: list[
            CapabilityPerformanceObservation
        ],
    ) -> CapabilityPerformanceSummary:
        attempts = len(observations)
        successes = sum(
            1 for item in observations if item.succeeded
        )
        failures = attempts - successes

        durations = [
            float(item.duration_ms)
            for item in observations
            if item.duration_ms is not None
        ]
        total_duration_ms = sum(durations)

        failure_kinds = [
            item.failure_kind
            for item in observations
            if not item.succeeded
        ]

        last_failure = next(
            (
                item
                for item in reversed(observations)
                if not item.succeeded
            ),
            None,
        )

        fallback_correlations = {
            item.correlation_id
            for item in observations
            if item.fallback_used
        }

        return CapabilityPerformanceSummary(
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            tenant_id=tenant_id,
            attempts=attempts,
            successes=successes,
            failures=failures,
            timeouts=failure_kinds.count("timeout"),
            unavailable=failure_kinds.count("unavailable"),
            circuit_open=failure_kinds.count("circuit_open"),
            provider_errors=failure_kinds.count(
                "provider_error"
            ),
            other_failures=sum(
                1
                for kind in failure_kinds
                if kind
                not in {
                    "timeout",
                    "unavailable",
                    "circuit_open",
                    "provider_error",
                }
            ),
            fallback_eligible_failures=sum(
                1
                for item in observations
                if not item.succeeded
                and item.fallback_allowed
            ),
            fallback_invocations=len(
                fallback_correlations
            ),
            total_duration_ms=total_duration_ms,
            average_duration_ms=(
                total_duration_ms / len(durations)
                if durations
                else 0.0
            ),
            success_rate=(
                successes / attempts
                if attempts
                else 0.0
            ),
            last_error_code=(
                last_failure.error_code
                if last_failure
                else None
            ),
            last_failure_kind=(
                last_failure.failure_kind
                if last_failure
                else None
            ),
            last_observed_at_ts=max(
                (
                    item.observed_at_ts
                    for item in observations
                ),
                default=None,
            ),
        )


class CapabilityPerformanceReporter:
    """
    Reporter adapter projecting final outcomes into performance evidence.
    """

    def __init__(
        self,
        *,
        store: InMemoryCapabilityPerformanceStore,
        projector: CapabilityPerformanceProjector | None = None,
    ) -> None:
        self.store = store
        self.projector = (
            projector or CapabilityPerformanceProjector()
        )

    async def report(
        self,
        outcome: CapabilityExecutionOutcome,
    ) -> None:
        self.store.record_many(
            self.projector.project(outcome)
        )


__all__ = [
    "CapabilityPerformanceObservation",
    "CapabilityPerformanceObservationStatus",
    "CapabilityPerformanceProjector",
    "CapabilityPerformanceReporter",
    "CapabilityPerformanceSummary",
    "InMemoryCapabilityPerformanceStore",
]
