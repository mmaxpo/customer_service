from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.planner.runtime.plan_evaluator import PlanEvaluator
from app.tcos.planner.runtime.plan_generator import PlanGenerator
from app.tcos.planner.runtime.planning_context import PlanningContext


GOAL = "Summarize https://example.com"


def _context() -> PlanningContext:
    return PlanningContext(
        user_message=GOAL,
    )


def test_plan_evaluator_scores_candidates():
    generator = PlanGenerator()

    candidates = generator.generate(
        intent=detect_intent(text=GOAL),
        context=_context(),
    )

    assert candidates[0].score == 0.0

    evaluator = PlanEvaluator()

    candidates = evaluator.evaluate(candidates)

    assert candidates[0].score > 0.0


def test_planner_returns_highest_scored_plan():
    from app.tcos.planner.runtime.planner import Planner

    planner = Planner()

    candidate = planner.plan(
        intent=detect_intent(text=GOAL),
        context=_context(),
    )

    assert candidate.business_plan.goal.title
