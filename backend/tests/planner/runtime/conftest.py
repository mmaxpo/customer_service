import pytest

from app.tcos.planner.memory import PlanningMemory


@pytest.fixture(autouse=True)
def clear_planning_memory_between_tests():
    PlanningMemory().clear()
    yield
    PlanningMemory().clear()
