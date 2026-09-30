from app.tcos.planner.memory import PlanningMemory
from app.tcos.planner.runtime.intent import detect_intent


def test_planning_memory_returns_empty_list_by_default():
    memory = PlanningMemory()

    result = memory.retrieve(
        intent=detect_intent(text="Reply to customer"),
        context=None,
    )

    assert result == []
