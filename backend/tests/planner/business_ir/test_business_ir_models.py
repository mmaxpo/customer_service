from app.tcos.planner.business_ir import (
    BusinessEdge,
    BusinessGoal,
    BusinessPlan,
    BusinessTask,
    BusinessTaskCategory,
    CapabilityReference,
)


def test_business_plan_model_accepts_atomic_tasks_and_capabilities():
    plan = BusinessPlan(
        id="plan_refund",
        goal=BusinessGoal(
            id="goal_refund",
            title="Refund customer",
            success_conditions=["Refund exists", "Customer notified"],
        ),
        tasks=[
            BusinessTask(
                id="retrieve_order",
                name="Retrieve order",
                category=BusinessTaskCategory.INFORMATION,
                required_capabilities=[
                    CapabilityReference(capability_id="shopify.get_order")
                ],
            ),
            BusinessTask(
                id="notify_customer",
                name="Notify customer",
                category=BusinessTaskCategory.COMMUNICATION,
                required_capabilities=[
                    CapabilityReference(capability_id="runtime.response")
                ],
            ),
        ],
        edges=[
            BusinessEdge(
                id="e1",
                source="retrieve_order",
                target="notify_customer",
            )
        ],
    )

    assert plan.schema_version == "business_ir.v1"
    assert (
        plan.tasks[0].required_capabilities[0].capability_id
        == "shopify.get_order"
    )
