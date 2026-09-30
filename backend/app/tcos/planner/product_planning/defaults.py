from app.tcos.planner.product_planning.registry import (
    ProductPlannerRegistry,
)


def build_default_product_planner_registry() -> ProductPlannerRegistry:
    """
    Build the product-neutral initial-planning registry.

    Product modules register their own planners outside this core
    package. The generic default therefore starts empty.
    """

    return ProductPlannerRegistry()
