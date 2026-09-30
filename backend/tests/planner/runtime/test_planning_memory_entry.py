from app.tcos.planner.business_ir.generic_examples import build_url_summary_business_plan
from app.tcos.planner.memory import PlanningMemoryEntry
from app.tcos.planner.runtime.plan_candidate import PlanCandidate


def _candidate() -> PlanCandidate:
    return PlanCandidate(
        id="candidate",
        source="template",
        business_plan=build_url_summary_business_plan("Summarize https://example.com"),
    )


def test_planning_memory_entry_defaults():
    entry = PlanningMemoryEntry(
        id="entry_1",
        intent_name="customer_reply",
        candidate=_candidate(),
    )

    assert entry.success_count == 0
    assert entry.failure_count == 0
    assert entry.total_count == 0
    assert entry.success_rate == 0.0
    assert entry.confidence == 1.0


def test_planning_memory_entry_success_rate():
    entry = PlanningMemoryEntry(
        id="entry_1",
        intent_name="customer_reply",
        candidate=_candidate(),
        success_count=8,
        failure_count=2,
    )

    assert entry.total_count == 10
    assert entry.success_rate == 0.8
