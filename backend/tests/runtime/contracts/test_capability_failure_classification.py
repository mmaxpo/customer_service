from app.integrations.errors import (
    IntegrationCircuitOpenError,
    IntegrationProviderError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)
from app.runtime.capabilities.execution import (
    classify_integration_failure,
)


def test_timeout_is_transient_fallback_candidate():
    failure = classify_integration_failure(
        IntegrationTimeoutError("timeout")
    )

    assert failure.error_code == "capability_provider_timeout"
    assert failure.transient is True
    assert failure.fallback_candidate is True


def test_unavailable_is_transient_fallback_candidate():
    failure = classify_integration_failure(
        IntegrationUnavailableError("unavailable")
    )

    assert failure.error_code == (
        "capability_provider_unavailable"
    )
    assert failure.transient is True
    assert failure.fallback_candidate is True


def test_circuit_open_is_transient_fallback_candidate():
    failure = classify_integration_failure(
        IntegrationCircuitOpenError("open")
    )

    assert failure.error_code == (
        "capability_provider_circuit_open"
    )
    assert failure.transient is True
    assert failure.fallback_candidate is True


def test_generic_provider_error_is_not_fallback_candidate():
    failure = classify_integration_failure(
        IntegrationProviderError("provider failed")
    )

    assert failure.error_code == "capability_provider_error"
    assert failure.transient is False
    assert failure.fallback_candidate is False
