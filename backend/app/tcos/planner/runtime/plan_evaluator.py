from __future__ import annotations

from app.tcos.planner.runtime.plan_candidate import PlanCandidate


class PlanEvaluator:
    """
    Responsible for evaluating candidate plans.

    Future scoring inputs:

    - business policy
    - execution cost
    - estimated latency
    - required capabilities
    - success history
    - merchant preferences
    - LLM reasoning
    """

    def evaluate(
        self,
        candidates: list[PlanCandidate],
    ) -> list[PlanCandidate]:

        for candidate in candidates:
            score = 0.0

            if candidate.source in {"template", "capability_reasoner"}:
                score += 1.0

            score += candidate.metrics.get("historical_bonus", 0)

            candidate.score = score

        return candidates
