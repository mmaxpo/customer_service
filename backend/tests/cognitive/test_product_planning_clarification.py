from __future__ import annotations

import pytest

from app.domains.customer_service.services.support.planning.customer_support_product_planner_registry import (
    register_customer_support_product_planner,
)
from app.runtime.capabilities.registry.defaults import (
    build_default_capability_registry,
)
from app.tcos.cognitive import (
    CognitiveRuntime,
    CognitiveSessionStatus,
)
from app.tcos.planner.product_planning import (
    build_default_product_planner_registry,
)


def _runtime() -> CognitiveRuntime:
    products = build_default_product_planner_registry()

    register_customer_support_product_planner(products)

    capabilities = build_default_capability_registry()

    return CognitiveRuntime(
        product_planners=products,
        is_semantic_capability=(capabilities.has_capability),
    )


def test_clarification_is_completed_not_failed():
    session = _runtime().execute_goal(
        goal=("My order hasn't arrived. Check it for me.")
    )

    assert session.status == (CognitiveSessionStatus.COMPLETED)

    assert session.execution_session is None
    assert session.planner_session is not None

    assert session.planner_session["status"] == ("clarification_required")

    assert (
        session.planner_session["clarification"]["reason_code"] == "missing_order_ref"
    )

    event_types = [event.type for event in session.events]

    assert "CognitiveClarificationRequired" in (event_types)
    assert "ExecutionPrepared" not in event_types
    assert "CognitiveSessionFailed" not in event_types


@pytest.mark.asyncio
async def test_runtime_clarification_never_executes_workflow():
    session = await _runtime().execute_goal_runtime(
        goal=("My order hasn't arrived. Check it for me."),
        ctx=object(),
    )

    assert session.status == (CognitiveSessionStatus.COMPLETED)

    assert session.execution_session is None

    assert (
        session.metrics.get(
            "runtime_executed",
            False,
        )
        is False
    )

    assert session.planner_session is not None
    assert session.planner_session["status"] == ("clarification_required")
