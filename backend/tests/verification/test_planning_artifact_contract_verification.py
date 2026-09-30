from app.tcos.planner.business_ir.models import (
    BusinessGoal,
    BusinessPlan,
    BusinessTaskCategory,
)
from app.tcos.planner.business_ir.factory import task_with_capability
from app.tcos.planner.runtime.plan_candidate import PlanCandidate
from app.tcos.verification import VerificationEngine


def test_verification_engine_rejects_missing_planning_artifact_producer():
    task = task_with_capability(
        task_id="reply",
        name="Reply from missing summary",
        category=BusinessTaskCategory.COMMUNICATION,
        capability_id="runtime.response",
    ).model_copy(
        update={
            "metadata": {
                "config": {
                    "answer_from": "missing_summary",
                }
            }
        }
    )

    candidate = PlanCandidate(
        id="candidate_missing_artifact",
        source="test",
        business_plan=BusinessPlan(
            id="missing_artifact_plan",
            goal=BusinessGoal(id="goal", title="Goal"),
            tasks=[task],
        ),
    )

    result = VerificationEngine().verify(candidate)

    assert result.passed is False
    assert any(issue.code == "missing_artifact_producer" for issue in result.issues)


def test_verification_engine_passes_valid_url_summary_artifact_contract():
    from app.tcos.planner.business_ir.generic_examples import (
        build_url_summary_business_plan,
    )

    candidate = PlanCandidate(
        id="candidate_url_summary",
        source="test",
        business_plan=build_url_summary_business_plan(
            "Summarize this URL for me: https://example.com"
        ),
    )

    result = VerificationEngine().verify(candidate)

    assert result.passed is True
    assert not any(issue.code == "missing_artifact_producer" for issue in result.issues)
