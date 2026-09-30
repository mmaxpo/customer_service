from app.tcos.planner.runtime import PlannerRuntime


GOAL = "Summarize https://example.com"


def test_plan_goal_is_core_runtime_entrypoint():
    session = PlannerRuntime().plan_goal(
        goal=GOAL,
    )

    assert session.status.value == "compiled"
    assert session.business_plan is not None
    assert session.business_plan.id == "url_summary_plan"


def test_plan_customer_reply_remains_backward_compatible_alias():
    canonical = PlannerRuntime().plan_goal(
        goal=GOAL,
    )

    compatibility = (
        PlannerRuntime()
        .plan_customer_reply(
            goal=GOAL,
        )
    )

    assert compatibility.status == canonical.status
    assert (
        compatibility.business_plan.id
        == canonical.business_plan.id
    )
