from app.runtime.objectives.repair.registry import (
    ObjectiveRepairPlannerRegistry,
)


def build_default_objective_repair_registry(
) -> ObjectiveRepairPlannerRegistry:
    """
    Build the product-neutral objective-repair registry.

    Product modules register their own planners outside this
    core package. The generic default therefore starts empty.
    """

    return ObjectiveRepairPlannerRegistry()


__all__ = [
    "build_default_objective_repair_registry",
]
