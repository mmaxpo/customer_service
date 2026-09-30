from app.tcos.planner.business_ir import BusinessGoal, BusinessPlan
from app.tcos.planner.runtime.plan_candidate import PlanCandidate
from app.tcos.verification.business_plan import verify_business_plan_candidate


def test_business_plan_verification_rejects_empty_plan():
    candidate = PlanCandidate(
        id="empty",
        source="test",
        business_plan=BusinessPlan(
            id="p",
            goal=BusinessGoal(id="g", title="Goal"),
            tasks=[],
        ),
    )

    result = verify_business_plan_candidate(candidate)

    assert result.passed is False
    assert any(issue.code == "no_tasks" for issue in result.issues)
