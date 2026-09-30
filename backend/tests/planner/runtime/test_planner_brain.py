from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.planner.runtime.planner import Planner
from app.tcos.planner.runtime.planning_context import PlanningContext


GOAL = "Summarize https://example.com"


def test_planner_returns_business_plan():
    planner = Planner()

    candidate = planner.plan(
        intent=detect_intent(text=GOAL),
        context=PlanningContext(
            user_message=GOAL,
        ),
    )

    assert candidate.business_plan.goal.title
    assert len(candidate.business_plan.tasks) > 0
