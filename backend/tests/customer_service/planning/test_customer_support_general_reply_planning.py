from app.cognitive_runtime import (
    build_application_cognitive_runtime,
)
from app.domains.customer_service.services.support.planning.customer_support_product_planner import (
    CustomerSupportProductPlanner,
)
from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)


def _plan(message: str):
    return CustomerSupportProductPlanner().plan(
        intent=detect_intent(text=message),
        context=PlanningContext(
            user_message=message,
        ),
    )


def test_general_customer_reply_is_product_owned():
    result = _plan(
        "Reply to the customer and thank them."
    )

    assert result.claimed is True
    assert result.requires_clarification is False

    candidate = result.candidates[0]

    assert (
        candidate.source
        == "customer_service_product_planner"
    )

    assert (
        candidate.metrics["selected_capability"]
        == "customer_service.customer_reply"
    )


def test_general_reply_plan_uses_generic_execution_building_blocks():
    result = _plan(
        "Answer this customer using our knowledge base."
    )

    plan = result.candidates[0].business_plan

    assert [task.id for task in plan.tasks] == [
        "search_knowledge",
        "generate_reply",
        "send_response",
    ]

    assert [
        task.required_capabilities[0].capability_id
        for task in plan.tasks
    ] == [
        "agent_tool.knowledge_search",
        "runtime.agent_custom",
        "runtime.response",
    ]


def test_non_customer_unknown_goal_is_not_claimed():
    result = _plan(
        "Build a quarterly revenue forecast"
    )

    assert result.claimed is False


def test_application_uses_product_not_core_for_general_reply():
    session = (
        build_application_cognitive_runtime()
        .execute_goal(
            goal="Reply to the customer and thank them.",
            user_id="user_1",
        )
    )

    planner = session.planner_session

    assert planner["status"] == "compiled"

    candidate = planner["selected_candidate"]

    assert (
        candidate["source"]
        == "customer_service_product_planner"
    )

    assert (
        candidate["metrics"]["selected_capability"]
        == "customer_service.customer_reply"
    )
