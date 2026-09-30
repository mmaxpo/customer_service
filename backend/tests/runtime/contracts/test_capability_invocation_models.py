from app.runtime.capabilities.models import (
    CapabilityInvocation,
    CapabilityInvocationStatus,
    CapabilityResult,
)


def test_capability_invocation_model_defaults():
    invocation = CapabilityInvocation(
        capability_id="shopify.get_order",
        inputs={"order_ref": "#1001"},
        user_id="user_1",
    )

    assert invocation.capability_id == "shopify.get_order"
    assert invocation.inputs["order_ref"] == "#1001"
    assert invocation.user_id == "user_1"
    assert invocation.correlation_id
    assert invocation.metadata == {}
    assert invocation.created_at_ts > 0


def test_capability_result_ok_contract():
    result = CapabilityResult(
        status=CapabilityInvocationStatus.OK,
        capability_id="shopify.get_order",
        output={"order_name": "#1001"},
        duration_ms=12.5,
        metadata={"source": "cache"},
    )

    assert result.ok is True
    assert result.status == "ok"
    assert result.output["order_name"] == "#1001"
    assert result.error_code is None
    assert result.error_message is None
    assert result.duration_ms == 12.5
    assert result.metadata["source"] == "cache"


def test_capability_result_error_contract():
    result = CapabilityResult(
        status=CapabilityInvocationStatus.ERROR,
        capability_id="shopify.get_order",
        error_code="missing_order_ref",
        error_message="order_ref is required",
    )

    assert result.ok is False
    assert result.status == "error"
    assert result.output is None
    assert result.error_code == "missing_order_ref"
    assert result.error_message == "order_ref is required"
