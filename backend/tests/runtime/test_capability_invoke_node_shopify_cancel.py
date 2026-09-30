from types import SimpleNamespace

import pytest

from app.runtime.nodes.builtins.capability import (
    CapabilityInvokeConfig,
    CapabilityInvokeNode,
)
from app.runtime.capabilities.models import CapabilityInvocation


class _RecordingCapabilities:
    def __init__(self, output):
        self.output = output
        self.calls = []

    async def resolve(self, invocation: CapabilityInvocation):
        self.calls.append(invocation)
        return SimpleNamespace(
            model_dump=lambda mode="json": {
                "status": "ok",
                "capability_id": invocation.capability_id,
                "output": self.output,
                "error_code": None,
                "error_message": None,
                "duration_ms": 1.0,
                "metadata": {},
            }
        )


class _Services:
    def __init__(self, capabilities):
        self.capabilities = capabilities


class _Ctx:
    def __init__(self, services, user_id="user-1"):
        self._services = services
        self.user_id = user_id


@pytest.mark.asyncio
async def test_capability_invoke_node_merges_vars_order_ref_into_payload(
    monkeypatch,
):
    capabilities = _RecordingCapabilities(
        output={"status": "prepared", "order_id": "gid://shopify/Order/1"}
    )
    services = _Services(capabilities)

    monkeypatch.setattr(
        "app.runtime.nodes.builtins.capability.get_runtime_services",
        lambda ctx: services,
    )

    config = CapabilityInvokeConfig(
        capability_id="ecommerce.orders.action",
        payload={
            "action": "cancel",
            "reason": "Customer support workflow decision",
            "idempotency_key": "cs:shopify:cancel:#1001",
        },
        input_from="vars",
        input_key="order_ref",
        save_as="shopify_action",
    )

    result = await CapabilityInvokeNode().run(
        _Ctx(services),
        {"vars": {"order_ref": "#1001"}},
        config,
    )

    assert len(capabilities.calls) == 1
    invocation = capabilities.calls[0]

    assert invocation.capability_id == "ecommerce.orders.action"
    assert invocation.inputs["action"] == "cancel"
    assert invocation.inputs["order_ref"] == "#1001"
    assert invocation.inputs["idempotency_key"] == "cs:shopify:cancel:#1001"
    assert invocation.user_id == "user-1"

    assert result["meta"]["ok"] is True
    assert result["patch"]["vars"]["shopify_action"]["status"] == "prepared"
