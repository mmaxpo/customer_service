from types import SimpleNamespace

import pytest

from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.execution import (
    CapabilityExecutorRegistry,
    DeterministicProviderTrafficAllocator,
    ProviderCandidateScore,
    ProviderScoringResult,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.registry import (
    CapabilityRisk,
    build_default_system,
)


def competitive_scoring():
    return ProviderScoringResult(
        capability_id="ecommerce.orders.get",
        selected_provider_id="shopify",
        selected_provider_ref="shopify.get_order",
        scoring_applied=True,
        reason="performance_ranked",
        candidates=(
            ProviderCandidateScore(
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref="shopify.get_order",
                binding_priority=100,
                attempts=20,
                successes=20,
                success_rate=1.0,
                average_duration_ms=50.0,
                evidence_available=True,
                evidence_sufficient=True,
                confidence=1.0,
                priority_score=1.0,
                reliability_score=1.0,
                latency_score=0.9,
                final_score=0.95,
                selection_reason="performance_weighted",
            ),
            ProviderCandidateScore(
                capability_id="ecommerce.orders.get",
                provider_id="mock",
                provider_ref="mock.get_order",
                binding_priority=10,
                attempts=20,
                successes=20,
                success_rate=1.0,
                average_duration_ms=45.0,
                evidence_available=True,
                evidence_sufficient=True,
                confidence=1.0,
                priority_score=0.0,
                reliability_score=1.0,
                latency_score=1.0,
                final_score=0.92,
                selection_reason="performance_weighted",
            ),
        ),
    )


def test_same_allocation_key_always_selects_same_provider():
    system = build_default_system(
        include_mock_provider=True
    )
    allocator = DeterministicProviderTrafficAllocator()

    kwargs = {
        "user_id": "user_1",
        "tenant_id": "tenant_1",
        "capability_id": "ecommerce.orders.get",
        "correlation_id": "correlation-stable",
        "capability_risk": CapabilityRisk.SAFE,
        "bindings": (
            system.bindings.list_for_capability(
                "ecommerce.orders.get"
            )
        ),
        "scoring": competitive_scoring(),
    }

    first = allocator.allocate(**kwargs)
    second = allocator.allocate(**kwargs)

    assert first.allocation_applied is True
    assert second.allocation_applied is True
    assert first.bucket == second.bucket
    assert (
        first.selected_provider_id
        == second.selected_provider_id
    )
    assert first.candidates == second.candidates


def test_large_score_gap_preserves_top_ranked_provider():
    scoring = competitive_scoring().model_copy(
        update={
            "candidates": (
                competitive_scoring().candidates[0],
                competitive_scoring().candidates[1]
                .model_copy(
                    update={"final_score": 0.50}
                ),
            )
        }
    )
    system = build_default_system(
        include_mock_provider=True
    )

    result = DeterministicProviderTrafficAllocator(
    ).allocate(
        user_id="user_1",
        tenant_id="tenant_1",
        capability_id="ecommerce.orders.get",
        correlation_id="correlation-gap",
        capability_risk=CapabilityRisk.SAFE,
        bindings=(
            system.bindings.list_for_capability(
                "ecommerce.orders.get"
            )
        ),
        scoring=scoring,
    )

    assert result.allocation_applied is False
    assert result.selected_provider_id == "shopify"
    assert result.reason == (
        "fewer_than_two_competitive_providers"
    )


def test_insufficient_evidence_disables_allocation():
    scoring = competitive_scoring().model_copy(
        update={
            "candidates": tuple(
                item.model_copy(
                    update={
                        "evidence_sufficient": False
                    }
                )
                for item in competitive_scoring().candidates
            )
        }
    )
    system = build_default_system(
        include_mock_provider=True
    )

    result = DeterministicProviderTrafficAllocator(
    ).allocate(
        user_id="user_1",
        tenant_id="tenant_1",
        capability_id="ecommerce.orders.get",
        correlation_id="correlation-insufficient",
        capability_risk=CapabilityRisk.SAFE,
        bindings=(
            system.bindings.list_for_capability(
                "ecommerce.orders.get"
            )
        ),
        scoring=scoring,
    )

    assert result.allocation_applied is False
    assert result.selected_provider_id == "shopify"


def test_high_risk_capability_never_allocates():
    system = build_default_system(
        include_mock_provider=True
    )

    result = DeterministicProviderTrafficAllocator(
    ).allocate(
        user_id="user_1",
        tenant_id="tenant_1",
        capability_id="ecommerce.orders.get",
        correlation_id="correlation-high-risk",
        capability_risk=CapabilityRisk.HIGH,
        bindings=(
            system.bindings.list_for_capability(
                "ecommerce.orders.get"
            )
        ),
        scoring=competitive_scoring(),
    )

    assert result.allocation_applied is False
    assert result.reason == "capability_not_safe"


class CompetitiveFakeScorer:
    async def score_candidates(self, **kwargs):
        return competitive_scoring()


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
async def test_runtime_exposes_allocation_diagnostics():
    calls = []
    invocation = CapabilityInvocation(
        capability_id="ecommerce.orders.get",
        inputs={"order_ref": "#1001"},
        correlation_id="runtime-allocation-stable",
    )

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(
            include_mock_provider=True
        ),
        executor_registry=build_executors(calls),
        provider_performance_scorer=(
            CompetitiveFakeScorer()
        ),
        provider_traffic_allocator=(
            DeterministicProviderTrafficAllocator()
        ),
    )

    first = await resolver.resolve(invocation)
    second = await resolver.resolve(invocation)

    assert first.ok is True
    assert second.ok is True
    assert calls[0] == calls[1]

    first_allocation = (
        first.metadata["resolution"]["metadata"]
        ["provider_allocation"]
    )
    second_allocation = (
        second.metadata["resolution"]["metadata"]
        ["provider_allocation"]
    )

    assert first_allocation["allocation_applied"] is True
    assert (
        first_allocation["selected_provider_id"]
        == second_allocation["selected_provider_id"]
    )
    assert (
        first_allocation["bucket"]
        == second_allocation["bucket"]
    )
    assert len(first_allocation["candidates"]) == 2


@pytest.mark.asyncio
async def test_health_rejects_allocated_provider_and_uses_healthy_alternative():
    from datetime import datetime, timezone

    from app.runtime.capabilities.execution import (
        ProviderHealthSnapshot,
    )

    class MockSelectingAllocator:
        def allocate(self, **kwargs):
            scoring = kwargs["scoring"]

            return __import__(
                "app.runtime.capabilities.execution",
                fromlist=["ProviderAllocationResult"],
            ).ProviderAllocationResult(
                capability_id=kwargs["capability_id"],
                allocation_applied=True,
                reason="test_allocated_mock",
                selected_provider_id="mock",
                selected_provider_ref="mock.get_order",
                allocation_key=(
                    "tenant_1|user_1|ecommerce.orders.get|"
                    "allocation-health-test"
                ),
                bucket=9000,
                candidates=(),
            )

    class FakeHealthReader:
        def __init__(self):
            self.calls = []

        async def get_effective_health(self, **kwargs):
            self.calls.append(kwargs)

            state = (
                "unhealthy"
                if kwargs["provider_id"] == "mock"
                else "healthy"
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

    calls = []
    health_reader = FakeHealthReader()

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(
            include_mock_provider=True
        ),
        executor_registry=build_executors(calls),
        provider_performance_scorer=(
            CompetitiveFakeScorer()
        ),
        provider_traffic_allocator=(
            MockSelectingAllocator()
        ),
        provider_health_reader=health_reader,
        provider_health_mode="enforce_unhealthy",
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
            correlation_id="allocation-health-test",
        )
    )

    assert result.ok is True

    # Allocation selected mock, but health rejected it before execution.
    assert calls == ["shopify"]
    assert result.output == {
        "provider": "shopify",
    }
    assert result.metadata["selected_provider_id"] == (
        "shopify"
    )
    assert result.metadata["fallback_used"] is False

    assert [
        item["provider_id"]
        for item in health_reader.calls
    ] == ["mock", "shopify"]

    resolution = result.metadata["resolution"]

    allocation = (
        resolution["metadata"]
        ["provider_allocation"]
    )

    assert allocation["allocation_applied"] is True
    assert allocation["selected_provider_id"] == "mock"
    assert allocation["reason"] == "test_allocated_mock"
    assert allocation["bucket"] == 9000

    rejections = {
        item["provider_id"]: item
        for item in resolution["rejected_providers"]
    }

    assert rejections["mock"]["reason"] == (
        "provider_unhealthy_scoped"
    )
    assert (
        rejections["mock"]["metadata"]
        ["effective_state"]
        == "unhealthy"
    )

    enforcement = (
        resolution["metadata"]
        ["provider_health_enforcement"]
    )

    assert enforcement["rejected_count"] == 1
    assert (
        enforcement["rejected_providers"][0]
        ["provider_id"]
        == "mock"
    )

    attempts = result.metadata["execution_attempts"]
    assert len(attempts) == 1
    assert attempts[0]["provider_id"] == "shopify"
    assert attempts[0]["outcome"] == "success"
