from __future__ import annotations

from app.domains.customer_service.services.support.planning.customer_support_product_planner import (
    CUSTOMER_SUPPORT_PRODUCT_ID,
    CustomerSupportProductPlanner,
)
from app.domains.customer_service.services.support.planning.customer_support_product_planner_registry import (
    register_customer_support_product_planner,
)
from app.tcos.planner.product_planning import (
    ProductPlanner,
    ProductPlannerRegistry,
    build_default_product_planner_registry,
)
from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.planner.runtime.planning_inputs import (
    build_default_planning_context,
)


def test_customer_support_planner_implements_core_contract():
    planner = CustomerSupportProductPlanner()

    assert isinstance(planner, ProductPlanner)
    assert planner.product_id == CUSTOMER_SUPPORT_PRODUCT_ID


def test_customer_support_registration_is_product_owned():
    registry = ProductPlannerRegistry()

    register_customer_support_product_planner(registry)

    planner = registry.resolve("customer_service")

    assert isinstance(
        planner,
        CustomerSupportProductPlanner,
    )


def test_customer_support_registration_does_not_change_core_default():
    core_registry = build_default_product_planner_registry()

    assert core_registry.registered_product_ids() == ()

    register_customer_support_product_planner(core_registry)

    assert core_registry.registered_product_ids() == ("customer_service",)


def test_registered_customer_support_planner_claims_shipping():
    context = build_default_planning_context(
        user_message="Reply to customer: Where is my order #1001?"
    )
    intent = detect_intent(
        text=context.user_message,
    )

    result = CustomerSupportProductPlanner().plan(
        intent=intent,
        context=context,
    )

    assert result.product_id == "customer_service"
    assert result.claimed is True
    assert len(result.candidates) == 1
    assert result.clarification is None
