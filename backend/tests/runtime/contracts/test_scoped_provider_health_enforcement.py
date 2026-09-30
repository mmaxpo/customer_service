from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.execution import (
    CapabilityExecutorRegistry,
    ProviderHealthEnforcementMode,
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
        states=None,
        *,
        fail=False,
    ):
        self.states = states or {}
        self.fail = fail
        self.calls = []

    async def get_effective_health(self, **kwargs):
        self.calls.append(kwargs)

        if self.fail:
            raise RuntimeError("health reader unavailable")

        state = self.states.get(
            kwargs["provider_id"],
            "healthy",
        )

        return ProviderHealthSnapshot(
            found=True,
            user_id=kwargs["user_id"],
            tenant_id=kwargs["tenant_id"],
            capability_id=kwargs["capability_id"],
            provider_id=kwargs["provider_id"],
            provider_ref=kwargs["provider_ref"],
            current_state=state,
            effective_state=state,
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


def build_executors(calls):
    executors = CapabilityExecutorRegistry()

    async def shopify_executor(context):
        calls.append("shopify")
        return {"provider": "shopify"}

    async def mock_executor(context):
        calls.append("mock")
        return {"provider": "mock"}

    executors.register(
        "shopify.get_order",
        shopify_executor,
    )
    executors.register(
        "shopify.order_action",
        shopify_executor,
    )
    executors.register(
        "mock.get_order",
        mock_executor,
    )

    return executors


@pytest.mark.asyncio
async def test_off_mode_does_not_read_health():
    calls = []
    reader = FakeHealthReader({"shopify": "unhealthy"})

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(),
        executor_registry=build_executors(calls),
        provider_health_reader=reader,
        provider_health_mode=(ProviderHealthEnforcementMode.OFF),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert calls == ["shopify"]
    assert reader.calls == []

    health = result.metadata["resolution"]["metadata"]["provider_health"]
    assert health["mode"] == "off"
    assert health["read_attempted"] is False


@pytest.mark.asyncio
async def test_enforce_unhealthy_selects_healthy_alternative():
    calls = []
    reader = FakeHealthReader(
        {
            "shopify": "unhealthy",
            "mock": "healthy",
        }
    )

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(include_mock_provider=True),
        executor_registry=build_executors(calls),
        provider_health_reader=reader,
        provider_health_mode="enforce_unhealthy",
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.output == {"provider": "mock"}
    assert calls == ["mock"]
    assert [item["provider_id"] for item in reader.calls] == ["shopify", "mock"]

    assert result.metadata["selected_provider_id"] == "mock"
    assert result.metadata["fallback_used"] is False
    assert len(result.metadata["execution_attempts"]) == 1

    rejected = {
        item["provider_id"]: item["reason"]
        for item in (result.metadata["resolution"]["rejected_providers"])
    }
    assert rejected["shopify"] == ("provider_unhealthy_scoped")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state",
    ["healthy", "degraded"],
)
async def test_enforcement_keeps_non_unhealthy_states(
    state,
):
    calls = []
    reader = FakeHealthReader({"shopify": state})

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(),
        executor_registry=build_executors(calls),
        provider_health_reader=reader,
        provider_health_mode="enforce_unhealthy",
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert calls == ["shopify"]
    assert result.metadata["selected_provider_id"] == "shopify"


@pytest.mark.asyncio
async def test_enforcement_reader_failure_is_fail_open():
    calls = []
    reader = FakeHealthReader(fail=True)

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(),
        executor_registry=build_executors(calls),
        provider_health_reader=reader,
        provider_health_mode="enforce_unhealthy",
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert calls == ["shopify"]

    health = result.metadata["resolution"]["metadata"]["provider_health"]
    assert health["read_succeeded"] is False
    assert health["fail_open"] is True
    assert health["selection_enforced"] is False


@pytest.mark.asyncio
async def test_unhealthy_without_alternative_fails_before_execution():
    calls = []
    reader = FakeHealthReader({"shopify": "unhealthy"})

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(),
        executor_registry=build_executors(calls),
        provider_health_reader=reader,
        provider_health_mode="enforce_unhealthy",
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is False
    assert result.error_code == ("no_capability_provider_available")
    assert calls == []
    assert result.metadata["execution_attempts"] == []

    rejected = {
        item["provider_id"]: item["reason"]
        for item in (result.metadata["resolution"]["rejected_providers"])
    }
    assert rejected["shopify"] == ("provider_unhealthy_scoped")


def test_invalid_enforcement_mode_is_rejected():
    with pytest.raises(
        ValueError,
        match="provider_health_mode",
    ):
        CapabilityResolver(
            services=build_services(),
            system=build_default_system(),
            executor_registry=(CapabilityExecutorRegistry()),
            provider_health_mode="invalid",
        )


@pytest.mark.asyncio
async def test_enforcement_restricts_recovering_without_lease():
    calls = []
    reader = FakeHealthReader({"shopify": "recovering"})

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(),
        executor_registry=build_executors(calls),
        provider_health_reader=reader,
        provider_health_mode="enforce_unhealthy",
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is False
    assert calls == []

    rejections = result.metadata["resolution"]["metadata"]["diagnostics"][
        "rejected_providers"
    ]

    recovering_rejection = next(
        item for item in rejections if item["provider_id"] == "shopify"
    )

    assert recovering_rejection["reason"] == "provider_recovering_scoped"
    assert recovering_rejection["metadata"]["effective_state"] == "recovering"


@pytest.mark.asyncio
async def test_recovering_without_lease_routes_safe_read_to_fallback():
    calls = []
    reader = FakeHealthReader(
        {
            "shopify": "recovering",
            "mock": "healthy",
        }
    )

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(
            include_mock_provider=True,
        ),
        executor_registry=build_executors(calls),
        provider_health_reader=reader,
        provider_health_mode="enforce_unhealthy",
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.output == {
        "provider": "mock",
    }

    # Shopify is denied before execution. Only the fallback executes.
    assert calls == ["mock"]
    assert result.metadata["selected_provider_id"] == "mock"
    assert result.metadata["provider_ref"] == "mock.get_order"

    # This is resolution-time health fallback, not fallback after an
    # execution failure.
    assert result.metadata["fallback_used"] is False
    assert len(result.metadata["execution_attempts"]) == 1
    assert result.metadata["execution_attempts"][0]["provider_id"] == "mock"

    resolution = result.metadata["resolution"]
    rejections = {
        item["provider_id"]: item for item in resolution["rejected_providers"]
    }

    assert rejections["shopify"]["reason"] == "provider_recovering_scoped"
    assert rejections["shopify"]["metadata"]["effective_state"] == "recovering"

    health_enforcement = resolution["metadata"]["provider_health_enforcement"]

    assert health_enforcement["rejected_count"] == 1
    assert health_enforcement["rejected_providers"][0]["provider_id"] == "shopify"
