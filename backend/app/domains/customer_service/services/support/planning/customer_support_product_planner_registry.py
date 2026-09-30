from __future__ import annotations

from app.domains.customer_service.services.support.planning.customer_support_product_planner import (
    CustomerSupportProductPlanner,
)
from app.tcos.planner.product_planning import (
    ProductPlannerRegistry,
)


def register_customer_support_product_planner(
    registry: ProductPlannerRegistry,
) -> None:
    """
    Register Customer Service initial planning with the generic Core.

    Product registration remains outside the generic TCOS package so
    the Core does not import Customer Service.
    """

    registry.register(CustomerSupportProductPlanner())


__all__ = [
    "register_customer_support_product_planner",
]
