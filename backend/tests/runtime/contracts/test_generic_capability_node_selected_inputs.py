from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.runtime.nodes.builtins.capability import (
    CapabilityInvokeConfig,
    CapabilityInvokeNode,
)
from app.runtime.resources import RuntimeServiceFactory
from app.runtime.capabilities.models import (
    CapabilityInvocationStatus,
    CapabilityResult,
)


class RecordingCapabilities:
    def __init__(self):
        self.invocation = None

    async def resolve(self, invocation):
        self.invocation = invocation

        return CapabilityResult(
            capability_id=invocation.capability_id,
            status=CapabilityInvocationStatus.OK,
            output={"ok": True},
        )


@pytest.mark.asyncio
async def test_selected_input_keys_only_enter_capability_payload():
    capabilities = RecordingCapabilities()

    services = RuntimeServiceFactory.build(user_id="user_1")
    services.capabilities = capabilities

    ctx = SimpleNamespace(
        user_id="user_1",
        services=services,
    )

    state = {
        "vars": {
            "order_ref": "#1001",
            "action": "shipping_status",
            "secret_unrelated_value": "do-not-forward",
        }
    }

    result = await CapabilityInvokeNode().run(
        ctx,
        state,
        CapabilityInvokeConfig(
            capability_id="ecommerce.orders.action",
            input_from="vars",
            input_keys=("order_ref", "action"),
            save_as="action_result",
        ),
    )

    assert capabilities.invocation is not None

    assert capabilities.invocation.inputs == {
        "order_ref": "#1001",
        "action": "shipping_status",
    }

    assert "secret_unrelated_value" not in (capabilities.invocation.inputs)

    assert result["patch"]["vars"]["action_result"] == {"ok": True}


@pytest.mark.asyncio
async def test_legacy_single_input_key_remains_supported():
    capabilities = RecordingCapabilities()

    services = RuntimeServiceFactory.build(user_id="user_1")
    services.capabilities = capabilities

    ctx = SimpleNamespace(
        user_id="user_1",
        services=services,
    )

    state = {
        "vars": {
            "order_ref": "#1001",
            "other": "ignored",
        }
    }

    await CapabilityInvokeNode().run(
        ctx,
        state,
        CapabilityInvokeConfig(
            capability_id="shopify.get_order",
            input_from="vars",
            input_key="order_ref",
            save_as="shopify_order",
        ),
    )

    assert capabilities.invocation.inputs == {"order_ref": "#1001"}
