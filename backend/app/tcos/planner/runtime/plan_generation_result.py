from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.tcos.planner.product_planning import (
    ProductPlanningResult,
)
from app.tcos.planner.runtime.plan_candidate import (
    PlanCandidate,
)


class PlanGenerationResult(BaseModel):
    """
    Core result of initial plan generation.

    Product planning may either:
    - claim and provide candidate plans,
    - claim and require clarification, or
    - decline ownership.

    If no Product claims the request, Core may use its
    compatibility/legacy planning path.
    """

    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    candidates: list[PlanCandidate] = Field(default_factory=list)

    product_result: ProductPlanningResult | None = None

    @property
    def product_claimed(self) -> bool:
        return self.product_result is not None and self.product_result.claimed

    @property
    def requires_clarification(self) -> bool:
        return (
            self.product_result is not None
            and self.product_result.requires_clarification
        )


__all__ = ["PlanGenerationResult"]
