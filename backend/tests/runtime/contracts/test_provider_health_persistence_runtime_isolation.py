from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.capabilities.execution.health.decisions import (
    ProviderHealthDecisionAction,
    ProviderHealthDecisionReason,
    ProviderHealthDecisionScope,
    ProviderHealthState,
    ProposedProviderHealthDecision,
)
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
)
from app.runtime.capabilities.execution.performance.reliability import (
    CapabilityReliabilityRecommendation,
)
from app.runtime.capabilities.registry.state import (
    ProviderHealthRegistry,
)


@pytest.mark.asyncio
async def test_durable_health_state_does_not_mutate_legacy_registry():
    user_id = uuid4()
    now = datetime.now(timezone.utc)
    registry = ProviderHealthRegistry()

    item = ProposedProviderHealthDecision(
        scope=ProviderHealthDecisionScope(
            user_id=str(user_id),
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        ),
        current_state=ProviderHealthState.HEALTHY,
        proposed_state=ProviderHealthState.UNHEALTHY,
        action=(
            ProviderHealthDecisionAction
            .PROPOSE_TRANSITION
        ),
        reason=(
            ProviderHealthDecisionReason
            .UNHEALTHY_CONFIRMED
        ),
        evidence_recommendation=(
            CapabilityReliabilityRecommendation
            .UNHEALTHY
        ),
        evidence_sufficient=True,
        attempts=20,
        successes=5,
        failures=15,
        success_rate=0.25,
        qualifying_windows=3,
        required_windows=3,
        window_start=now - timedelta(hours=1),
        window_end=now,
        evaluated_at=now,
        explanation="confirmed unhealthy evidence",
    )

    async with SessionLocal() as db:
        state, _, _ = (
            await CapabilityProviderHealthRepository(
                db
            ).persist_decision(
                decision=item
            )
        )

    assert state.current_state == "unhealthy"
    assert registry.is_healthy("shopify") is True
