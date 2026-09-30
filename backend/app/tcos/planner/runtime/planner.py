from __future__ import annotations

from app.tcos.planner.product_planning import (
    ProductPlannerRegistry,
)
from app.tcos.planner.runtime.intent import PlannerIntent
from app.tcos.planner.runtime.plan_candidate import (
    PlanCandidate,
)
from app.tcos.planner.runtime.plan_evaluator import PlanEvaluator
from app.tcos.planner.runtime.plan_generation_result import (
    PlanGenerationResult,
)
from app.tcos.planner.runtime.plan_generator import PlanGenerator
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)


class Planner:
    """
    Planner Brain.

    Responsible for deciding which candidate plan should be used.

    Product planners receive first claim authority when explicitly
    injected. If no Product claims the request, PlanGenerator keeps
    the existing compatibility planning path.
    """

    def __init__(
        self,
        *,
        product_planners: ProductPlannerRegistry | None = None,
    ) -> None:
        self._product_planners = product_planners

    def plan_result(
        self,
        *,
        intent: PlannerIntent,
        context: PlanningContext | None = None,
    ) -> PlanGenerationResult:
        result = PlanGenerator(
            product_planners=self._product_planners,
        ).generate_result(
            intent=intent,
            context=context,
        )

        if result.requires_clarification:
            return result

        candidates = PlanEvaluator().evaluate(result.candidates)

        candidates.sort(
            key=lambda candidate: candidate.score,
            reverse=True,
        )

        if not candidates:
            raise ValueError("Planner produced no candidate plans")

        return result.model_copy(
            update={
                "candidates": candidates,
            }
        )

    def plan(
        self,
        *,
        intent: PlannerIntent,
        context: PlanningContext | None = None,
    ) -> PlanCandidate:
        """
        Backward-compatible candidate-returning API.

        Product-aware live callers should use plan_result() so a
        clarification state cannot be collapsed into an exception
        or fallback.
        """

        result = self.plan_result(
            intent=intent,
            context=context,
        )

        if result.requires_clarification:
            raise ValueError(
                "Product planning requires clarification; "
                "use plan_result() to preserve that state."
            )

        return result.candidates[0]
