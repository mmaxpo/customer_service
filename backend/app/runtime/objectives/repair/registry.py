from __future__ import annotations

from app.runtime.objectives.repair.contracts import (
    ObjectiveRepairPlanner,
)


class ObjectiveRepairPlannerNotFoundError(
    LookupError
):
    pass


class ObjectiveRepairPlannerRegistry:
    """
    Deterministic product repair-planner registry keyed by
    normalized objective namespace and objective type.
    """

    def __init__(self) -> None:
        self._planners: dict[
            tuple[str, str],
            ObjectiveRepairPlanner,
        ] = {}

    def register(
        self,
        *,
        namespace: str,
        objective_type: str,
        planner: ObjectiveRepairPlanner,
    ) -> None:
        key = self._normalize_key(
            namespace=namespace,
            objective_type=objective_type,
        )

        if key in self._planners:
            raise ValueError(
                "objective repair planner already "
                "registered for "
                f"{key[0]}:{key[1]}"
            )

        if not isinstance(
            planner,
            ObjectiveRepairPlanner,
        ):
            raise TypeError(
                "planner must implement "
                "ObjectiveRepairPlanner"
            )

        self._planners[key] = planner

    def resolve(
        self,
        *,
        namespace: str,
        objective_type: str,
    ) -> ObjectiveRepairPlanner:
        key = self._normalize_key(
            namespace=namespace,
            objective_type=objective_type,
        )

        planner = self._planners.get(key)

        if planner is None:
            raise ObjectiveRepairPlannerNotFoundError(
                "objective repair planner not found for "
                f"{key[0]}:{key[1]}"
            )

        return planner

    def contains(
        self,
        *,
        namespace: str,
        objective_type: str,
    ) -> bool:
        key = self._normalize_key(
            namespace=namespace,
            objective_type=objective_type,
        )
        return key in self._planners

    def registered_keys(
        self,
    ) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(self._planners))

    @staticmethod
    def _normalize_key(
        *,
        namespace: str,
        objective_type: str,
    ) -> tuple[str, str]:
        normalized_namespace = str(
            namespace
        ).strip().lower()

        normalized_objective_type = str(
            objective_type
        ).strip().lower()

        if not normalized_namespace:
            raise ValueError(
                "objective repair namespace is required"
            )

        if not normalized_objective_type:
            raise ValueError(
                "objective repair type is required"
            )

        return (
            normalized_namespace,
            normalized_objective_type,
        )


__all__ = [
    "ObjectiveRepairPlannerNotFoundError",
    "ObjectiveRepairPlannerRegistry",
]
