from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.errors import (
    IntegrationTimeoutError,
)
from app.runtime.capabilities.invoker import CapabilityInvoker
from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.execution import (
    CapabilityExecutorRegistry,
    InMemoryCapabilityOutcomeReporter,
    ProviderHealthProbeClaim,
    ProviderHealthProbeCompletion,
    ProviderHealthSnapshot,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.registry import (
    build_default_system,
)


class UnhealthyReader:
    async def get_effective_health(self, **kwargs):
        return ProviderHealthSnapshot(
            found=True,
            user_id=kwargs.get("user_id"),
            tenant_id=kwargs.get("tenant_id"),
            capability_id=kwargs["capability_id"],
            provider_id=kwargs["provider_id"],
            provider_ref=kwargs["provider_ref"],
            current_state="unhealthy",
            effective_state="unhealthy",
            observed_at=datetime.now(timezone.utc),
        )


class CompletingCoordinator:
    def __init__(
        self,
        *,
        completion_raises=False,
    ):
        self.completion_raises = completion_raises
        self.claim_calls = []
        self.completion_calls = []

    async def try_claim_probe(self, **kwargs):
        self.claim_calls.append(kwargs)

        return ProviderHealthProbeClaim(
            acquired=True,
            reason="probe_lease_acquired",
            scope_key="scope",
            lease_token="probe-token",
            lease_until=None,
            claimed_at=datetime.now(timezone.utc),
            current_state="unhealthy",
        )

    async def complete_probe(self, **kwargs):
        self.completion_calls.append(kwargs)

        if self.completion_raises:
            raise RuntimeError("probe completion unavailable")

        return ProviderHealthProbeCompletion(
            completed=True,
            reason=("probe_succeeded" if kwargs["succeeded"] else "probe_failed"),
            scope_key="scope",
            lease_token=kwargs["lease_token"],
            succeeded=kwargs["succeeded"],
            previous_state="unhealthy",
            resulting_state=("recovering" if kwargs["succeeded"] else "unhealthy"),
            completed_at=datetime.now(timezone.utc),
            state_version=2,
        )


def build_services(user_id):
    return SimpleNamespace(
        identity=SimpleNamespace(
            user_id=user_id,
            tenant_id="tenant_invoker_probe",
        ),
        business=SimpleNamespace(),
    )


def build_registry(*, fail=False):
    registry = CapabilityExecutorRegistry()

    async def executor(context):
        if fail:
            raise IntegrationTimeoutError("probe timed out")

        return {"order_ref": (context.invocation.inputs["order_ref"])}

    registry.register(
        "shopify.get_order",
        executor,
    )
    registry.register(
        "shopify.order_action",
        executor,
    )
    return registry


@pytest.mark.asyncio
async def test_invoker_completes_successful_probe():
    user_id = uuid4()
    coordinator = CompletingCoordinator()
    reporter = InMemoryCapabilityOutcomeReporter()

    invoker = CapabilityInvoker(
        resolver=CapabilityResolver(
            services=build_services(user_id),
            system=build_default_system(),
            executor_registry=build_registry(),
            provider_health_reader=UnhealthyReader(),
            provider_health_probe_coordinator=(coordinator),
            provider_health_mode=("enforce_unhealthy"),
        ),
        outcome_reporter=reporter,
    )

    result = await invoker.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
            user_id=user_id,
        )
    )

    assert result.ok is True
    assert len(coordinator.completion_calls) == 1
    assert coordinator.completion_calls[0]["succeeded"] is True
    assert result.metadata["health_probe_completion"]["reason"] == "probe_succeeded"

    assert len(reporter.outcomes) == 1
    assert reporter.outcomes[0].attempts[0].health_probe is True


@pytest.mark.asyncio
async def test_invoker_completes_failed_probe():
    user_id = uuid4()
    coordinator = CompletingCoordinator()

    invoker = CapabilityInvoker(
        resolver=CapabilityResolver(
            services=build_services(user_id),
            system=build_default_system(),
            executor_registry=build_registry(fail=True),
            provider_health_reader=UnhealthyReader(),
            provider_health_probe_coordinator=(coordinator),
            provider_health_mode=("enforce_unhealthy"),
        ),
    )

    result = await invoker.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
            user_id=user_id,
        )
    )

    assert result.ok is False
    assert len(coordinator.completion_calls) == 1

    call = coordinator.completion_calls[0]
    assert call["succeeded"] is False
    assert call["failure_kind"] == "timeout"
    assert result.metadata["health_probe_completion"]["reason"] == "probe_failed"


@pytest.mark.asyncio
async def test_probe_completion_failure_never_changes_result():
    user_id = uuid4()
    coordinator = CompletingCoordinator(completion_raises=True)

    invoker = CapabilityInvoker(
        resolver=CapabilityResolver(
            services=build_services(user_id),
            system=build_default_system(),
            executor_registry=build_registry(),
            provider_health_reader=UnhealthyReader(),
            provider_health_probe_coordinator=(coordinator),
            provider_health_mode=("enforce_unhealthy"),
        ),
    )

    result = await invoker.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
            user_id=user_id,
        )
    )

    assert result.ok is True
    assert result.output["order_ref"] == "#1001"
    assert (
        result.metadata["health_probe_completion"]["reason"]
        == "probe_completion_failed_open"
    )


class RecoveringReader:
    async def get_effective_health(self, **kwargs):
        return ProviderHealthSnapshot(
            found=True,
            user_id=kwargs.get("user_id"),
            tenant_id=kwargs.get("tenant_id"),
            capability_id=kwargs["capability_id"],
            provider_id=kwargs["provider_id"],
            provider_ref=kwargs["provider_ref"],
            current_state="recovering",
            effective_state="recovering",
            observed_at=datetime.now(timezone.utc),
        )


class RecoveringCoordinator(CompletingCoordinator):
    async def try_claim_probe(self, **kwargs):
        self.claim_calls.append(kwargs)

        return ProviderHealthProbeClaim(
            acquired=True,
            reason="recovery_lease_acquired",
            scope_key="scope",
            lease_token="recovery-token",
            lease_until=None,
            claimed_at=datetime.now(timezone.utc),
            current_state="recovering",
        )

    async def complete_probe(self, **kwargs):
        self.completion_calls.append(kwargs)

        return ProviderHealthProbeCompletion(
            completed=True,
            reason=(
                "recovery_request_succeeded"
                if kwargs["succeeded"]
                else "recovery_request_failed"
            ),
            scope_key="scope",
            lease_token=kwargs["lease_token"],
            succeeded=kwargs["succeeded"],
            previous_state="recovering",
            resulting_state=("recovering" if kwargs["succeeded"] else "unhealthy"),
            completed_at=datetime.now(timezone.utc),
            state_version=3,
        )


@pytest.mark.asyncio
async def test_invoker_controls_recovering_provider_request():
    user_id = uuid4()
    coordinator = RecoveringCoordinator()

    invoker = CapabilityInvoker(
        resolver=CapabilityResolver(
            services=build_services(user_id),
            system=build_default_system(),
            executor_registry=build_registry(),
            provider_health_reader=(RecoveringReader()),
            provider_health_probe_coordinator=(coordinator),
            provider_health_mode=("enforce_unhealthy"),
        ),
    )

    result = await invoker.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
            user_id=user_id,
        )
    )

    assert result.ok is True
    assert len(coordinator.claim_calls) == 1
    assert len(coordinator.completion_calls) == 1

    attempt = result.metadata["execution_attempts"][0]

    assert attempt["health_probe"] is True
    assert attempt["health_probe_lease_token"] == "recovery-token"

    diagnostic = result.metadata["resolution"]["metadata"]["provider_health"]

    assert diagnostic["effective_state"] == "recovering"
    assert diagnostic["enforcement_reason"] == "controlled_recovery_request"
    assert (
        result.metadata["health_probe_completion"]["reason"]
        == "recovery_request_succeeded"
    )
