from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.execution import (
    CapabilityExecutorRegistry,
    ProviderHealthSnapshot,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.registry import (
    build_default_system,
)


class FakeHealthReader:
    def __init__(
        self,
        *,
        effective_state="unhealthy",
        fail=False,
    ):
        self.effective_state = effective_state
        self.fail = fail
        self.calls = []

    async def get_effective_health(self, **kwargs):
        self.calls.append(kwargs)

        if self.fail:
            raise RuntimeError("health reader unavailable")

        return ProviderHealthSnapshot(
            found=True,
            user_id=kwargs["user_id"],
            tenant_id=kwargs["tenant_id"],
            capability_id=kwargs["capability_id"],
            provider_id=kwargs["provider_id"],
            provider_ref=kwargs["provider_ref"],
            current_state=self.effective_state,
            effective_state=self.effective_state,
            observed_at=datetime.now(timezone.utc),
        )


def build_services():
    return SimpleNamespace(
        identity=SimpleNamespace(
            user_id="user_1",
            tenant_id="tenant_1",
        ),
        business=SimpleNamespace(),
    )


@pytest.mark.asyncio
async def test_unhealthy_shadow_does_not_change_selection():
    reader = FakeHealthReader(
        effective_state="unhealthy"
    )
    executors = CapabilityExecutorRegistry()

    async def shopify_executor(context):
        return {"provider": "shopify"}

    executors.register(
        "shopify.get_order",
        shopify_executor,
    )
    executors.register(
        "shopify.order_action",
        shopify_executor,
    )

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(),
        executor_registry=executors,
        provider_health_reader=reader,
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.output == {"provider": "shopify"}
    assert result.metadata["selected_provider_id"] == (
        "shopify"
    )

    shadow = (
        result.metadata["resolution"]["metadata"]
        ["provider_health_shadow"]
    )

    assert shadow["effective_state"] == "unhealthy"
    assert shadow["selection_enforced"] is False
    assert shadow["selected_provider_unchanged"] is True
    assert len(reader.calls) == 1


@pytest.mark.asyncio
async def test_shadow_reader_failure_does_not_break_execution():
    reader = FakeHealthReader(fail=True)
    executors = CapabilityExecutorRegistry()

    async def shopify_executor(context):
        return {"provider": "shopify"}

    executors.register(
        "shopify.get_order",
        shopify_executor,
    )
    executors.register(
        "shopify.order_action",
        shopify_executor,
    )

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(),
        executor_registry=executors,
        provider_health_reader=reader,
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True

    shadow = (
        result.metadata["resolution"]["metadata"]
        ["provider_health_shadow"]
    )

    assert shadow["read_succeeded"] is False
    assert shadow["error_type"] == "RuntimeError"
    assert shadow["selection_enforced"] is False
