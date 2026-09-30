from types import SimpleNamespace

import pytest

from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.execution import (
    CapabilityExecutorRegistry,
    NullProviderPerformanceScorer,
    ProviderCandidateScore,
    ProviderScoringResult,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.registry import (
    build_default_system,
)


class FakePerformanceScorer:
    def __init__(self, selected_provider_id):
        self.selected_provider_id = selected_provider_id
        self.calls = []

    async def score_candidates(self, **kwargs):
        self.calls.append(kwargs)

        candidates = tuple(kwargs["candidates"])
        selected = next(
            item
            for item in candidates
            if item.provider_id
            == self.selected_provider_id
        )

        return ProviderScoringResult(
            capability_id=kwargs["capability_id"],
            selected_provider_id=selected.provider_id,
            selected_provider_ref=selected.provider_ref,
            scoring_applied=True,
            reason="test_performance_ranked",
            candidates=tuple(
                ProviderCandidateScore(
                    capability_id=item.capability_id,
                    provider_id=item.provider_id,
                    provider_ref=item.provider_ref,
                    binding_priority=item.priority,
                    attempts=20,
                    successes=20,
                    success_rate=1.0,
                    average_duration_ms=10.0,
                    evidence_available=True,
                    evidence_sufficient=True,
                    confidence=1.0,
                    priority_score=(
                        1.0
                        if item.provider_id == "shopify"
                        else 0.0
                    ),
                    reliability_score=1.0,
                    latency_score=1.0,
                    final_score=(
                        1.0
                        if item.provider_id
                        == self.selected_provider_id
                        else 0.5
                    ),
                    selection_reason="test_score",
                )
                for item in candidates
            ),
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
async def test_null_scorer_preserves_binding_priority():
    system = build_default_system(
        include_mock_provider=True
    )
    candidates = system.bindings.list_for_capability(
        "ecommerce.orders.get"
    )

    result = await NullProviderPerformanceScorer(
    ).score_candidates(
        user_id="user_1",
        tenant_id="tenant_1",
        capability_id="ecommerce.orders.get",
        candidates=candidates,
    )

    assert result.scoring_applied is False
    assert result.fallback_to_priority is True
    assert result.selected_provider_id == "shopify"
    assert [
        item.provider_id for item in result.candidates
    ] == ["shopify", "mock"]


@pytest.mark.asyncio
async def test_runtime_uses_scored_eligible_provider():
    calls = []
    scorer = FakePerformanceScorer("mock")

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(
            include_mock_provider=True
        ),
        executor_registry=build_executors(calls),
        provider_performance_scorer=scorer,
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert calls == ["mock"]
    assert result.metadata["selected_provider_id"] == "mock"

    scoring = (
        result.metadata["resolution"]["metadata"]
        ["provider_scoring"]
    )
    assert scoring["scoring_applied"] is True
    assert (
        scoring["selected_provider_id"]
        == "mock"
    )

    assert len(scorer.calls) == 1
    assert {
        item.provider_id
        for item in scorer.calls[0]["candidates"]
    } == {"shopify", "mock"}


@pytest.mark.asyncio
async def test_scoring_only_receives_structurally_eligible_candidates():
    calls = []
    scorer = FakePerformanceScorer("mock")
    system = build_default_system(
        include_mock_provider=True
    )

    # Shopify cannot satisfy this explicit allow-list, so it must never enter
    # scoring even though it has the higher binding priority.
    invocation = CapabilityInvocation(
        capability_id="ecommerce.orders.get",
        inputs={"order_ref": "#1001"},
        metadata={
            "allowed_provider_ids": ["mock"],
        },
    )

    resolver = CapabilityResolver(
        services=build_services(),
        system=system,
        executor_registry=build_executors(calls),
        provider_performance_scorer=scorer,
    )

    # Runtime invocation metadata is not yet mapped to the semantic request's
    # allow-list, so prove eligibility using a denied provider in the retry
    # path directly.
    (
        scoring,
        eligible_bindings,
    ) = await resolver._score_eligible_providers(
        invocation=invocation,
        denied_provider_ids=("shopify",),
    )

    assert scoring["selected_provider_id"] == "mock"
    assert [
        item.provider_id
        for item in eligible_bindings
    ] == ["mock"]
    assert [
        item.provider_id
        for item in scorer.calls[0]["candidates"]
    ] == ["mock"]


@pytest.mark.asyncio
async def test_database_scorer_prefers_reliable_lower_priority_provider():
    from datetime import datetime, timezone
    from uuid import uuid4

    from app.core.session import SessionLocal
    from app.platform.events.event_store import (
        PlatformEventStore,
    )
    from app.runtime.capabilities.execution import (
        CapabilityPerformanceObservation,
        CapabilityPerformanceObservationRepository,
        CapabilityPerformanceObservationStatus,
        DatabaseProviderPerformanceScorer,
    )

    user_id = uuid4()
    tenant_id = f"tenant-scoring-{uuid4()}"
    system = build_default_system(
        include_mock_provider=True
    )
    candidates = system.bindings.list_for_capability(
        "ecommerce.orders.get"
    )
    observed_at = datetime.now(timezone.utc)

    async def record(
        *,
        db,
        provider_id,
        attempt_index,
        succeeded,
        duration_ms,
    ):
        correlation_id = (
            f"{provider_id}-{attempt_index}-{uuid4()}"
        )
        event = await PlatformEventStore(db).append(
            user_id=user_id,
            event_type=(
                "runtime.capability.execution.completed"
            ),
            source="runtime.capabilities",
            payload={},
            meta={
                "correlation_id": correlation_id,
            },
        )

        observation = CapabilityPerformanceObservation(
            correlation_id=correlation_id,
            attempt_index=0,
            requested_capability_id=(
                "ecommerce.orders.get"
            ),
            resolved_capability_id=(
                "ecommerce.orders.get"
            ),
            provider_id=provider_id,
            provider_ref=f"{provider_id}.get_order",
            status=(
                CapabilityPerformanceObservationStatus
                .SUCCEEDED
                if succeeded
                else CapabilityPerformanceObservationStatus
                .FAILED
            ),
            succeeded=succeeded,
            duration_ms=duration_ms,
            failure_kind=(
                None if succeeded else "provider_error"
            ),
            tenant_id=tenant_id,
            observed_at_ts=observed_at.timestamp(),
        )

        inserted = await (
            CapabilityPerformanceObservationRepository(
                db
            ).record_many(
                source_event_id=event.id,
                observations=[observation],
            )
        )
        assert inserted == 1

    async with SessionLocal() as db:
        # Higher-priority Shopify has materially weaker evidence.
        for index in range(10):
            await record(
                db=db,
                provider_id="shopify",
                attempt_index=index,
                succeeded=index < 6,
                duration_ms=400.0,
            )

        # Lower-priority mock is consistently successful and faster.
        for index in range(10):
            await record(
                db=db,
                provider_id="mock",
                attempt_index=index,
                succeeded=True,
                duration_ms=40.0,
            )

        result = await DatabaseProviderPerformanceScorer(
            db,
            minimum_attempts=10,
        ).score_candidates(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id="ecommerce.orders.get",
            candidates=candidates,
            observed_at=(
                observed_at
                + __import__("datetime").timedelta(
                    seconds=1
                )
            ),
        )

    assert result.scoring_applied is True
    assert result.selected_provider_id == "mock"
    assert result.selected_provider_ref == (
        "mock.get_order"
    )

    scores = {
        item.provider_id: item
        for item in result.candidates
    }

    assert scores["mock"].attempts == 10
    assert scores["mock"].success_rate == 1.0
    assert scores["mock"].evidence_sufficient is True
    assert scores["mock"].final_score > (
        scores["shopify"].final_score
    )


@pytest.mark.asyncio
async def test_database_scorer_does_not_use_other_tenant_evidence():
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    from app.core.session import SessionLocal
    from app.platform.events.event_store import (
        PlatformEventStore,
    )
    from app.runtime.capabilities.execution import (
        CapabilityPerformanceObservation,
        CapabilityPerformanceObservationRepository,
        CapabilityPerformanceObservationStatus,
        DatabaseProviderPerformanceScorer,
    )

    user_id = uuid4()
    requested_tenant = f"tenant-requested-{uuid4()}"
    other_tenant = f"tenant-other-{uuid4()}"
    observed_at = datetime.now(timezone.utc)

    system = build_default_system(
        include_mock_provider=True
    )
    candidates = system.bindings.list_for_capability(
        "ecommerce.orders.get"
    )

    async with SessionLocal() as db:
        for index in range(10):
            correlation_id = f"other-{index}-{uuid4()}"

            event = await PlatformEventStore(db).append(
                user_id=user_id,
                event_type=(
                    "runtime.capability.execution.completed"
                ),
                source="runtime.capabilities",
                payload={},
                meta={
                    "correlation_id": correlation_id,
                },
            )

            observation = CapabilityPerformanceObservation(
                correlation_id=correlation_id,
                attempt_index=0,
                requested_capability_id=(
                    "ecommerce.orders.get"
                ),
                resolved_capability_id=(
                    "ecommerce.orders.get"
                ),
                provider_id="mock",
                provider_ref="mock.get_order",
                status=(
                    CapabilityPerformanceObservationStatus
                    .SUCCEEDED
                ),
                succeeded=True,
                duration_ms=1.0,
                tenant_id=other_tenant,
                observed_at_ts=observed_at.timestamp(),
            )

            await (
                CapabilityPerformanceObservationRepository(
                    db
                ).record_many(
                    source_event_id=event.id,
                    observations=[observation],
                )
            )

        result = await DatabaseProviderPerformanceScorer(
            db,
            minimum_attempts=10,
        ).score_candidates(
            user_id=str(user_id),
            tenant_id=requested_tenant,
            capability_id="ecommerce.orders.get",
            candidates=candidates,
            observed_at=(
                observed_at + timedelta(seconds=1)
            ),
        )

    assert result.scoring_applied is False
    assert result.fallback_to_priority is True
    assert result.reason == "no_performance_evidence"
    assert result.selected_provider_id == "shopify"


@pytest.mark.asyncio
async def test_low_volume_evidence_has_bounded_influence():
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    from app.core.session import SessionLocal
    from app.platform.events.event_store import (
        PlatformEventStore,
    )
    from app.runtime.capabilities.execution import (
        CapabilityPerformanceObservation,
        CapabilityPerformanceObservationRepository,
        CapabilityPerformanceObservationStatus,
        DatabaseProviderPerformanceScorer,
    )

    user_id = uuid4()
    tenant_id = f"tenant-confidence-{uuid4()}"
    observed_at = datetime.now(timezone.utc)

    system = build_default_system(
        include_mock_provider=True
    )
    candidates = system.bindings.list_for_capability(
        "ecommerce.orders.get"
    )

    async with SessionLocal() as db:
        correlation_id = f"one-success-{uuid4()}"
        event = await PlatformEventStore(db).append(
            user_id=user_id,
            event_type=(
                "runtime.capability.execution.completed"
            ),
            source="runtime.capabilities",
            payload={},
            meta={"correlation_id": correlation_id},
        )

        observation = CapabilityPerformanceObservation(
            correlation_id=correlation_id,
            attempt_index=0,
            requested_capability_id=(
                "ecommerce.orders.get"
            ),
            resolved_capability_id=(
                "ecommerce.orders.get"
            ),
            provider_id="mock",
            provider_ref="mock.get_order",
            status=(
                CapabilityPerformanceObservationStatus
                .SUCCEEDED
            ),
            succeeded=True,
            duration_ms=1.0,
            tenant_id=tenant_id,
            observed_at_ts=observed_at.timestamp(),
        )

        await CapabilityPerformanceObservationRepository(
            db
        ).record_many(
            source_event_id=event.id,
            observations=[observation],
        )

        result = await DatabaseProviderPerformanceScorer(
            db,
            minimum_attempts=10,
        ).score_candidates(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id="ecommerce.orders.get",
            candidates=candidates,
            observed_at=(
                observed_at + timedelta(seconds=1)
            ),
        )

    scores = {
        item.provider_id: item
        for item in result.candidates
    }

    assert scores["mock"].confidence == pytest.approx(
        0.1
    )
    assert scores["mock"].evidence_sufficient is False

    # One observation must not immediately overturn the configured
    # high-priority provider.
    assert result.selected_provider_id == "shopify"


@pytest.mark.asyncio
async def test_health_enforcement_rejects_scored_unhealthy_provider():
    from datetime import datetime, timezone

    from app.runtime.capabilities.execution import (
        ProviderHealthSnapshot,
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
    scorer = FakePerformanceScorer("mock")
    health_reader = FakeHealthReader()

    resolver = CapabilityResolver(
        services=build_services(),
        system=build_default_system(
            include_mock_provider=True
        ),
        executor_registry=build_executors(calls),
        provider_performance_scorer=scorer,
        provider_health_reader=health_reader,
        provider_health_mode="enforce_unhealthy",
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True

    # Performance scoring prefers mock, but durable health rejects it before
    # execution. Shopify is then selected and executes normally.
    assert calls == ["shopify"]
    assert result.output == {
        "provider": "shopify",
    }
    assert result.metadata["selected_provider_id"] == (
        "shopify"
    )
    assert result.metadata["provider_ref"] == (
        "shopify.get_order"
    )
    assert result.metadata["fallback_used"] is False

    assert [
        item["provider_id"]
        for item in health_reader.calls
    ] == ["mock", "shopify"]

    resolution = result.metadata["resolution"]
    scoring = resolution["metadata"]["provider_scoring"]

    # Preserve the original scoring decision for operational explanation.
    assert scoring["scoring_applied"] is True
    assert scoring["selected_provider_id"] == "mock"
    assert scoring["reason"] == (
        "test_performance_ranked"
    )

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

    health_enforcement = (
        resolution["metadata"]
        ["provider_health_enforcement"]
    )

    assert health_enforcement["rejected_count"] == 1
    assert (
        health_enforcement["rejected_providers"][0]
        ["provider_id"]
        == "mock"
    )

    attempts = result.metadata["execution_attempts"]
    assert len(attempts) == 1
    assert attempts[0]["provider_id"] == "shopify"
    assert attempts[0]["outcome"] == "success"
