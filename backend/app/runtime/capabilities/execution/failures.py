from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.integrations.errors import (
    IntegrationCircuitOpenError,
    IntegrationError,
    IntegrationProviderError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)


class CapabilityExecutionFailureKind(StrEnum):
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    CIRCUIT_OPEN = "circuit_open"
    PROVIDER_ERROR = "provider_error"
    UNKNOWN_INTEGRATION_ERROR = "unknown_integration_error"


@dataclass(frozen=True)
class CapabilityExecutionFailure:
    kind: CapabilityExecutionFailureKind
    error_code: str
    message: str
    transient: bool
    fallback_candidate: bool
    exception_type: str


def classify_integration_failure(
    exc: IntegrationError,
) -> CapabilityExecutionFailure:
    """
    Classify integration failures for capability execution.

    ProviderError is deliberately not considered a fallback candidate because
    IntegrationGateway currently wraps all general provider exceptions in it,
    including errors that may be validation, authorization, or business
    failures.
    """

    if isinstance(exc, IntegrationCircuitOpenError):
        return CapabilityExecutionFailure(
            kind=CapabilityExecutionFailureKind.CIRCUIT_OPEN,
            error_code="capability_provider_circuit_open",
            message=str(exc),
            transient=True,
            fallback_candidate=True,
            exception_type=type(exc).__name__,
        )

    if isinstance(exc, IntegrationTimeoutError):
        return CapabilityExecutionFailure(
            kind=CapabilityExecutionFailureKind.TIMEOUT,
            error_code="capability_provider_timeout",
            message=str(exc),
            transient=True,
            fallback_candidate=True,
            exception_type=type(exc).__name__,
        )

    if isinstance(exc, IntegrationUnavailableError):
        return CapabilityExecutionFailure(
            kind=CapabilityExecutionFailureKind.UNAVAILABLE,
            error_code="capability_provider_unavailable",
            message=str(exc),
            transient=True,
            fallback_candidate=True,
            exception_type=type(exc).__name__,
        )

    if isinstance(exc, IntegrationProviderError):
        return CapabilityExecutionFailure(
            kind=CapabilityExecutionFailureKind.PROVIDER_ERROR,
            error_code="capability_provider_error",
            message=str(exc),
            transient=False,
            fallback_candidate=False,
            exception_type=type(exc).__name__,
        )

    return CapabilityExecutionFailure(
        kind=CapabilityExecutionFailureKind.UNKNOWN_INTEGRATION_ERROR,
        error_code="capability_integration_error",
        message=str(exc),
        transient=False,
        fallback_candidate=False,
        exception_type=type(exc).__name__,
    )


__all__ = [
    "CapabilityExecutionFailure",
    "CapabilityExecutionFailureKind",
    "classify_integration_failure",
]
