from __future__ import annotations

from app.domains.customer_service.services.support.planning.customer_support_product_planner_registry import (
    register_customer_support_product_planner,
)
from app.tcos.planner.product_planning import (
    build_default_product_planner_registry,
)
from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.planner.runtime.plan_generator import (
    PlanGenerator,
)
from app.tcos.planner.runtime.planning_inputs import (
    build_default_planning_context,
)


def _generate(message: str):
    registry = build_default_product_planner_registry()

    register_customer_support_product_planner(registry)

    context = build_default_planning_context(
        user_message=message,
    )

    return PlanGenerator(
        product_planners=registry,
    ).generate_result(
        intent=detect_intent(text=context.user_message),
        context=context,
    )


def test_known_order_uses_product_candidate_not_legacy_shopify():
    result = _generate("Reply to customer: Where is order #1001?")

    assert result.product_claimed is True
    assert result.requires_clarification is False
    assert len(result.candidates) == 1

    candidate = result.candidates[0]

    assert candidate.source == ("customer_service_product_planner")

    payload = candidate.model_dump_json().lower()

    assert "ecommerce.orders.get" in payload
    assert "shopify.get_order" not in payload


def test_missing_order_is_authoritative_clarification():
    result = _generate("My order hasn't arrived. Check it for me.")

    assert result.product_claimed is True
    assert result.requires_clarification is True
    assert result.candidates == []

    clarification = result.product_result.clarification

    assert clarification is not None

    assert clarification.reason_code == ("missing_order_ref")

    assert clarification.missing_fields == ("order_ref",)


def test_general_customer_reply_uses_product_planner_not_legacy_fallback():
    result = _generate(
        "Reply to the customer and thank them."
    )

    assert result.product_claimed is True
    assert result.requires_clarification is False
    assert len(result.candidates) == 1

    candidate = result.candidates[0]

    assert (
        candidate.source
        == "customer_service_product_planner"
    )

    assert (
        candidate.metrics["selected_capability"]
        == "customer_service.customer_reply"
    )
