from app.tcos.planner.runtime.business_plan_builder import BusinessPlanBuilder
from app.tcos.planner.runtime.capability_reasoner import CapabilityReasoner
from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.planner.runtime.planning_inputs import build_default_planning_context




def test_business_plan_builder_preserves_operation_metadata():
    from app.tcos.planner.operations import (
        OperationType,
        PlanningOperation,
    )

    operation = PlanningOperation(
        id="fetch_source",
        capability_id="runtime.web_fetch_extract",
        operation_type=OperationType.ACQUIRE_INFORMATION,
        purpose="Fetch generic source information.",
        outputs=["source_text"],
        metadata={
            "test_marker": "preserved",
        },
    )

    plan = BusinessPlanBuilder().from_operations(
        plan_id="generic_metadata_plan",
        goal_title="Generic metadata preservation",
        operations=[operation],
    )

    first = plan.tasks[0]

    assert first.metadata["operation"]["outputs"] == [
        "source_text"
    ]
    assert (
        first.metadata["operation"]["capability_id"]
        == "runtime.web_fetch_extract"
    )
    assert first.metadata["test_marker"] == "preserved"
