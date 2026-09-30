from types import SimpleNamespace

import pytest

from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.execution import (
    CapabilityExecutorRegistry,
    CapabilityRuntimePolicy,
    CapabilityRuntimePolicySnapshot,
    ProviderCandidateScore,
    ProviderHealthSnapshot,
    ProviderScoringResult,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.registry import (
    build_default_system,
)


class FakePolicyReader:
    def __init__(
        self,
        *,
        capability_policy=None,
        provider_policy=None,
    ):
        self.capability_policy = (
            capability_policy
            or CapabilityRuntimePolicy()
        )
        self.provider_policy = (
            provider_policy
            or self.capability_policy
        )
        self.calls = []

    async def resolve_policy(self, **kwargs):
        self.calls.append(kwargs)
        policy = (
            self.provider_policy
            if kwargs.get("provider_id")
            else self.capability_policy
        )

        return CapabilityRuntimePolicySnapshot(
            found=True,
            user_id=kwargs.get("user_id"),
            tenant_id=kwargs.get("tenant_id"),
            capability_id=kwargs.get("capability_id"),
            provider_id=kwargs.get("provider_id"),
            provider_ref=kwargs.get("provider_ref"),
            effective_policy=policy,
            resolution_reason="test_policy",
        )


class CompetitiveScorer:
    async def score_candidates(self, **kwargs):
        candidates = {
            item.provider_id: item
            for item in kwargs["candidates"]
        }

        return ProviderScoringResult(
            capability_id=kwargs["capability_id"],
            selected_provider_id="shopify",
            selected_provider_ref="shopify.get_order",
            scoring_applied=True,
            reason="test_ranked",
            candidates=(
                ProviderCandidateScore(
                    capability_id=kwargs["capability_id"],
                    provider_id="shopify",
                    provider_ref="shopify.get_order",
                    binding_priority=candidates["shopify"].priority,
                    attempts=20,
                    successes=20,
                    success_rate=1.0,
                    average_duration_ms=40.0,
                    evidence_available=True,
                    evidence_sufficient=True,
                    confidence=1.0,
                    priority_score=1.0,
                    reliability_score=1.0,
                    latency_score=1.0,
                    final_score=0.95,
                    selection_reason="test",
                ),
                ProviderCandidateScore(
                    capability_id=kwargs["capability_id"],
                    provider_id="mock",
                    provider_ref="mock.get_order",
                    binding_priority=candidates["mock"].priority,
                    attempts=20,
                    successes=20,
                    success_rate=1.0,
                    average_duration_ms=45.0,
                    evidence_available=True,
                    evidence_sufficient=True,
                    confidence=1.0,
                    priority_score=0.0,
                    reliability_score=1.0,
                    latency_score=0.9,
                    final_score=0.93,
                    selection_reason="test",
                ),
            ),
        )


def build_services():
    return SimpleNamespace(
        identity=SimpleNamespace(
            user_id="user_1",
            tenant_id="tenant_1",
        ),
        business=SimpleNamespace(),
        db=None,
    )


def build_executors(calls):
    registry = CapabilityExecutorRegistry()

    async def shopify(context):
        calls.append("shopify")
        return {"provider": "shopify"}

    async def mock(context):
        calls.append("mock")
        return {"provider": "mock"}

    registry.register(
        "shopify.get_order",
        shopify,
    )
    registry.register(
        "shopify.order_action",
        shopify,
    )
    registry.register(
        "mock.get_order",
        mock,
    )
    return registry


@pytest.mark.asyncio
async def test_capability_policy_can_disable_allocation():
    calls = []
    policy_reader = FakePolicyReader(
        capability_policy=CapabilityRuntimePolicy(
            allocation_enabled=False,
        )
    )

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(
            include_mock_provider=True
        ),
        executor_registry=build_executors(calls),
        provider_performance_scorer=CompetitiveScorer(),
        capability_runtime_policy_reader=policy_reader,
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert calls == ["shopify"]

    resolution = result.metadata["resolution"]
    allocation = (
        resolution["metadata"]
        ["provider_allocation"]
    )
    policy = (
        resolution["metadata"]
        ["capability_runtime_policy"]
    )

    assert allocation["allocation_applied"] is False
    assert allocation["reason"] == (
        "disabled_by_runtime_policy"
    )
    assert (
        policy["effective_policy"]
        ["allocation_enabled"]
        is False
    )


@pytest.mark.asyncio
async def test_provider_policy_controls_health_enforcement():
    from datetime import datetime, timezone

    class UnhealthyReader:
        async def get_effective_health(self, **kwargs):
            return ProviderHealthSnapshot(
                found=True,
                user_id=kwargs["user_id"],
                tenant_id=kwargs["tenant_id"],
                capability_id=kwargs["capability_id"],
                provider_id=kwargs["provider_id"],
                provider_ref=kwargs["provider_ref"],
                current_state="unhealthy",
                effective_state="unhealthy",
                observed_at=datetime.now(timezone.utc),
            )

    calls = []
    policy_reader = FakePolicyReader(
        capability_policy=CapabilityRuntimePolicy(
            health_enforcement_mode="shadow",
            allocation_enabled=False,
        ),
        provider_policy=CapabilityRuntimePolicy(
            health_enforcement_mode=(
                "enforce_unhealthy"
            ),
            allocation_enabled=False,
        ),
    )

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(
            include_mock_provider=True
        ),
        executor_registry=build_executors(calls),
        provider_performance_scorer=CompetitiveScorer(),
        capability_runtime_policy_reader=policy_reader,
        provider_health_reader=UnhealthyReader(),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is False or calls != ["shopify"]

    resolution = result.metadata["resolution"]

    rejections = {
        item["provider_id"]: item
        for item in resolution["rejected_providers"]
    }
    shopify_rejection = rejections["shopify"]

    assert shopify_rejection["reason"] == (
        "provider_unhealthy_scoped"
    )

    provider_policy = (
        shopify_rejection["metadata"]
        ["runtime_policy"]
    )

    assert (
        provider_policy["effective_policy"]
        ["health_enforcement_mode"]
        == "enforce_unhealthy"
    )


@pytest.mark.asyncio
async def test_policy_reader_failure_fails_open():
    class FailingPolicyReader:
        async def resolve_policy(self, **kwargs):
            raise RuntimeError("policy store unavailable")

    calls = []

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(),
        executor_registry=build_executors(calls),
        capability_runtime_policy_reader=(
            FailingPolicyReader()
        ),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True

    policy = (
        result.metadata["resolution"]["metadata"]
        ["capability_runtime_policy"]
    )
    assert policy["found"] is False
    assert policy["resolution_reason"] == "code_defaults"
