from __future__ import annotations

from app.tcos.planner.business_ir.models import (
    BusinessEdge,
    BusinessGoal,
    BusinessPlan,
    BusinessTask,
    BusinessTaskCategory,
    CapabilityReference,
)
from app.tcos.planner.operations import (
    OperationType,
    PlanningOperation,
)


_OPERATION_CATEGORY_MAP = {
    OperationType.ACQUIRE_INFORMATION: (
        BusinessTaskCategory.INFORMATION
    ),
    OperationType.ANALYZE: (
        BusinessTaskCategory.COMMUNICATION
    ),
    OperationType.DECIDE: (
        BusinessTaskCategory.DECISION
    ),
    OperationType.EXECUTE: (
        BusinessTaskCategory.ACTION
    ),
    OperationType.COMMUNICATE: (
        BusinessTaskCategory.COMMUNICATION
    ),
}


class ProductBusinessPlanBuilder:
    """
    Public product-planning builder.

    Converts semantic PlanningOperation declarations into the generic
    BusinessPlan IR without exposing planner runtime implementation
    services to Product code.
    """

    def from_operations(
        self,
        *,
        plan_id: str,
        goal_title: str,
        operations: list[PlanningOperation],
        metadata: dict | None = None,
    ) -> BusinessPlan:
        tasks = [
            BusinessTask(
                id=operation.id,
                name=operation.purpose,
                category=_OPERATION_CATEGORY_MAP[
                    operation.operation_type
                ],
                required_capabilities=[
                    CapabilityReference(
                        capability_id=operation.capability_id
                    )
                ],
                metadata={
                    "operation": operation.model_dump(
                        mode="json"
                    ),
                    **operation.metadata,
                },
            )
            for operation in operations
        ]

        edges: list[BusinessEdge] = []
        operation_ids = {
            operation.id
            for operation in operations
        }

        for operation in operations:
            for dependency in operation.depends_on:
                if dependency not in operation_ids:
                    raise ValueError(
                        f"Operation `{operation.id}` depends "
                        f"on unknown operation `{dependency}`"
                    )

                edges.append(
                    BusinessEdge(
                        id=(
                            f"edge_{dependency}_to_"
                            f"{operation.id}"
                        ),
                        source=dependency,
                        target=operation.id,
                    )
                )

        return BusinessPlan(
            id=plan_id,
            goal=BusinessGoal(
                id=f"{plan_id}_goal",
                title=goal_title,
            ),
            tasks=tasks,
            edges=edges,
            metadata={
                "planning_strategy": (
                    "capability_operations"
                ),
                "extra": metadata or {},
            },
        )


__all__ = [
    "ProductBusinessPlanBuilder",
]
