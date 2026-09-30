from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.planner.runtime.plan_generator import PlanGenerator
from app.tcos.planner.runtime.planning_context import PlanningContext


GOAL = "Summarize https://example.com"


def test_plan_generator_returns_candidate():
    generator = PlanGenerator()

    candidates = generator.generate(
        intent=detect_intent(text=GOAL),
        context=PlanningContext(
            user_message=GOAL,
        ),
    )

    assert len(candidates) == 1
    assert candidates[0].source == "capability_reasoner"
    assert candidates[0].business_plan.goal.title
    assert candidates[0].score == 0.0
