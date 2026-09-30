from app.runtime.capabilities.models import (
    CapabilityInvocation,
    CapabilityInvocationStatus,
    CapabilityResult,
)
from app.runtime.capabilities.execution import (
    CapabilityExecutionOutcomeStatus,
    build_capability_execution_outcome,
)


def test_build_successful_capability_execution_outcome():
    invocation = CapabilityInvocation(
        capability_id="ecommerce.orders.get",
        inputs={"order_ref": "#1001"},
        user_id="user_1",
        metadata={"workflow_run_id": "run_1"},
    )

    result = CapabilityResult(
        status=CapabilityInvocationStatus.OK,
        capability_id=invocation.capability_id,
        output={"order_name": "#1001"},
        duration_ms=12.5,
        metadata={
            "resolved_capability_id": "ecommerce.orders.get",
            "selected_provider_id": "mock",
            "provider_ref": "mock.get_order",
            "fallback_used": True,
            "execution_attempts": [
                {
                    "provider_id": "shopify",
                    "provider_ref": "shopify.get_order",
                    "capability_id": "ecommerce.orders.get",
                    "outcome": "error",
                    "error_code": "capability_provider_timeout",
                    "failure_kind": "timeout",
                    "fallback_allowed": True,
                    "duration_ms": 5.0,
                },
                {
                    "provider_id": "mock",
                    "provider_ref": "mock.get_order",
                    "capability_id": "ecommerce.orders.get",
                    "outcome": "success",
                    "duration_ms": 2.0,
                },
            ],
        },
    )

    outcome = build_capability_execution_outcome(
        invocation=invocation,
        result=result,
        tenant_id="tenant_1",
    )

    assert outcome.status == (
        CapabilityExecutionOutcomeStatus.SUCCEEDED
    )
    assert outcome.ok is True
    assert outcome.fallback_used is True
    assert outcome.selected_provider_id == "mock"
    assert outcome.provider_ref == "mock.get_order"
    assert len(outcome.attempts) == 2
    assert outcome.attempts[0].failure_kind == "timeout"
    assert outcome.attempts[1].outcome == "success"
    assert outcome.user_id == "user_1"
    assert outcome.tenant_id == "tenant_1"


def test_build_failed_capability_execution_outcome():
    invocation = CapabilityInvocation(
        capability_id="ecommerce.orders.get",
    )

    result = CapabilityResult(
        status=CapabilityInvocationStatus.ERROR,
        capability_id=invocation.capability_id,
        error_code="unknown_capability",
        error_message="Capability is not registered",
        metadata={},
    )

    outcome = build_capability_execution_outcome(
        invocation=invocation,
        result=result,
    )

    assert outcome.status == (
        CapabilityExecutionOutcomeStatus.FAILED
    )
    assert outcome.ok is False
    assert outcome.error_code == "unknown_capability"
    assert outcome.attempts == []
