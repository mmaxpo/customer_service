from __future__ import annotations

from collections.abc import Callable

from app.tcos.capabilities.service import build_capability_registry
from app.tcos.planner.business_ir.models import BusinessPlan


def missing_capability_ids(
    plan: BusinessPlan,
    *,
    is_semantic_capability: (Callable[[str], bool] | None) = None,
    runtime_node_for_capability: (
        Callable[[str], str | None] | None
    ) = None,
) -> list[str]:
    """
    Return capability ids unknown to both accepted capability
    authorities.

    The legacy TCOS capability registry remains authoritative for
    existing Business IR capabilities.

    An optional semantic-capability predicate may extend capability
    existence during composition without coupling Business IR to the
    runtime capability-registry implementation.
    """

    registry = build_capability_registry()
    missing: set[str] = set()

    for task in plan.tasks:
        for ref in task.required_capabilities:
            capability_id = ref.capability_id

            try:
                registry.get(capability_id)
            except ValueError:
                if (
                    is_semantic_capability is not None
                    and is_semantic_capability(
                        capability_id
                    )
                ):
                    continue

                if (
                    runtime_node_for_capability is not None
                    and runtime_node_for_capability(
                        capability_id
                    )
                    is not None
                ):
                    continue

                missing.add(capability_id)

    return sorted(missing)


def capability_ids_for_plan(plan: BusinessPlan) -> list[str]:
    ids: set[str] = set()

    for task in plan.tasks:
        for ref in task.required_capabilities:
            ids.add(ref.capability_id)

    return sorted(ids)


def plan_capabilities_exist(
    plan: BusinessPlan,
    *,
    is_semantic_capability: (Callable[[str], bool] | None) = None,
    runtime_node_for_capability: (
        Callable[[str], str | None] | None
    ) = None,
) -> bool:
    return not missing_capability_ids(
        plan,
        is_semantic_capability=is_semantic_capability,
        runtime_node_for_capability=(
            runtime_node_for_capability
        ),
    )
