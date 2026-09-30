from __future__ import annotations

from app.tcos.planner.product_planning.contracts import (
    ProductPlanner,
)


class ProductPlannerNotFoundError(LookupError):
    pass


class ProductPlannerRegistry:
    """
    Explicit product-planner registry owned by the autonomous core.

    The generic core remains product-neutral. Product modules register
    their own ProductPlanner implementations during composition.
    """

    def __init__(self) -> None:
        self._planners: dict[str, ProductPlanner] = {}

    def register(self, planner: ProductPlanner) -> None:
        if not isinstance(planner, ProductPlanner):
            raise TypeError("planner must implement ProductPlanner")

        product_id = self._normalize_product_id(planner.product_id)

        if product_id in self._planners:
            raise ValueError(f"product planner already registered for {product_id}")

        self._planners[product_id] = planner

    def resolve(self, product_id: str) -> ProductPlanner:
        normalized = self._normalize_product_id(product_id)

        try:
            return self._planners[normalized]
        except KeyError as exc:
            raise ProductPlannerNotFoundError(
                f"product planner not found for {normalized}"
            ) from exc

    def contains(self, product_id: str) -> bool:
        normalized = self._normalize_product_id(product_id)
        return normalized in self._planners

    def registered_product_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._planners))

    @staticmethod
    def _normalize_product_id(value: str) -> str:
        normalized = str(value or "").strip().lower()

        if not normalized:
            raise ValueError("product_id is required")

        return normalized
