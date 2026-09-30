from app.tcos.planner.memory import PlanningMemory
from app.tcos.planner.runtime import PlannerRuntime, PlanningStatus
from app.tcos.planner.runtime.intent import detect_intent


def test_planner_runtime_records_successful_plan_to_memory():
    session = PlannerRuntime().plan_goal(goal="Summarize https://example.com")

    assert session.status == PlanningStatus.COMPILED

    memory_event = next(
        event for event in session.events if event.type == "PlanningMemoryRecorded"
    )

    assert memory_event.payload["outcome"] == "success"
    assert (
        memory_event.payload["candidate_id"]
        == "generated_generic_url_summary"
    )

    retrieved = PlanningMemory().retrieve(
        intent=detect_intent(text="Summarize https://example.com"),
        context=None,
    )

    assert len(retrieved) == 1
    assert retrieved[0].candidate.id == "generated_generic_url_summary"
    assert retrieved[0].metadata["success_count"] == 1
