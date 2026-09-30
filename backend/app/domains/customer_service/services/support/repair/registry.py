from app.domains.customer_service.services.support.repair.planner import (
    CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
    CUSTOMER_SUPPORT_OBJECTIVE_TYPES,
    CustomerSupportObjectiveRepairPlanner,
)
from app.runtime.objectives.repair import (
    ObjectiveRepairPlannerRegistry,
)


def register_customer_support_repair_planners(
    registry: ObjectiveRepairPlannerRegistry,
) -> None:
    planner = CustomerSupportObjectiveRepairPlanner()

    for objective_type in sorted(
        CUSTOMER_SUPPORT_OBJECTIVE_TYPES
    ):
        registry.register(
            namespace=(
                CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE
            ),
            objective_type=objective_type,
            planner=planner,
        )


__all__ = [
    "register_customer_support_repair_planners",
]
