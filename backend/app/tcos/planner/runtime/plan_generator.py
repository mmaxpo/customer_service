from __future__ import annotations

from app.tcos.planner.memory import PlanningMemory
from app.tcos.planner.product_planning import (
    ProductPlannerRegistry,
)
from app.tcos.planner.runtime.advisory_observation import (
    PlannerAdvisoryObserver,
)
from app.tcos.planner.runtime.business_plan_builder import (
    BusinessPlanBuilder,
)
from app.tcos.planner.runtime.capability_reasoner import (
    CapabilityReasoner,
)
from app.tcos.planner.runtime.intent import PlannerIntent
from app.tcos.planner.runtime.objective_candidate_observation import (
    ObjectiveCandidateObserver,
)
from app.tcos.planner.runtime.plan_candidate import PlanCandidate
from app.tcos.planner.runtime.plan_generation_result import (
    PlanGenerationResult,
)
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)


class PlanGenerator:
    def __init__(
        self,
        *,
        product_planners: ProductPlannerRegistry | None = None,
    ) -> None:
        self._product_planners = product_planners

    def generate_result(
        self,
        *,
        intent: PlannerIntent,
        context: PlanningContext | None = None,
    ) -> PlanGenerationResult:
        product_result = self._try_product_planners(
            intent=intent,
            context=context,
        )

        if product_result is not None:
            candidates = self._observe_candidates(
                product_result.candidates,
                context=context,
            )

            return PlanGenerationResult(
                candidates=candidates,
                product_result=product_result,
            )

        return PlanGenerationResult(
            candidates=self._legacy_candidates(
                intent=intent,
                context=context,
            ),
        )

    def generate(
        self,
        *,
        intent: PlannerIntent,
        context: PlanningContext | None = None,
    ) -> list[PlanCandidate]:
        """
        Backward-compatible candidate API.

        Live Product-aware planning should use generate_result()
        so clarification cannot be collapsed into an empty
        candidate list.
        """

        result = self.generate_result(
            intent=intent,
            context=context,
        )

        if result.requires_clarification:
            raise ValueError(
                "Product planning requires clarification; "
                "use generate_result() to preserve that state."
            )

        return result.candidates

    def _try_product_planners(
        self,
        *,
        intent: PlannerIntent,
        context: PlanningContext | None,
    ):
        registry = self._product_planners

        if registry is None:
            return None

        for product_id in registry.registered_product_ids():
            planner = registry.resolve(product_id)

            result = planner.plan(
                intent=intent,
                context=context,
            )

            if result.claimed:
                return result

        return None

    def _legacy_candidates(
        self,
        *,
        intent: PlannerIntent,
        context: PlanningContext | None,
    ) -> list[PlanCandidate]:
        memory_candidates = PlanningMemory().retrieve(
            intent=intent,
            context=context,
        )

        reasoning = CapabilityReasoner().reason(
            intent=intent,
            context=context,
        )

        plan = BusinessPlanBuilder().build(reasoning)

        generated = [
            PlanCandidate(
                id=(f"generated_{reasoning.selected_capability.replace('.', '_')}"),
                source="capability_reasoner",
                business_plan=plan,
                score=0.0,
                explanation=reasoning.reasoning,
                metrics={
                    "selected_capability": (reasoning.selected_capability),
                    "selection_confidence": (reasoning.confidence),
                    "capability_reasoning": (reasoning.model_dump(mode="json")),
                },
            )
        ]

        generated.extend(item.candidate for item in memory_candidates)

        return self._observe_candidates(
            generated,
            context=context,
        )

    @staticmethod
    def _observe_candidates(
        candidates: list[PlanCandidate],
        *,
        context: PlanningContext | None,
    ) -> list[PlanCandidate]:
        if not candidates:
            return []

        objective_observed = ObjectiveCandidateObserver().observe(
            candidates=candidates,
            context=context,
        )

        return PlannerAdvisoryObserver().observe(
            candidates=objective_observed,
            context=context,
        )
