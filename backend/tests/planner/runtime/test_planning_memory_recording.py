from app.tcos.planner.business_ir.generic_examples import build_url_summary_business_plan
from app.tcos.planner.memory import PlanningMemory
from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.planner.runtime.plan_candidate import PlanCandidate


def _candidate(candidate_id: str = "candidate") -> PlanCandidate:
    return PlanCandidate(
        id=candidate_id,
        source="template",
        business_plan=build_url_summary_business_plan("Summarize https://example.com"),
    )


def test_planning_memory_records_success():
    memory = PlanningMemory()
    memory.clear()

    entry = memory.record_success(
        intent_name="customer_reply",
        candidate=_candidate(),
        latency_ms=100,
        cost=0.01,
    )

    assert entry.success_count == 1
    assert entry.failure_count == 0
    assert entry.average_latency_ms == 100
    assert entry.average_cost == 0.01


def test_planning_memory_records_failure():
    memory = PlanningMemory()
    memory.clear()

    entry = memory.record_failure(
        intent_name="customer_reply",
        candidate=_candidate(),
    )

    assert entry.success_count == 0
    assert entry.failure_count == 1
    assert entry.success_rate == 0.0


def test_planning_memory_retrieves_matching_intent_candidates():
    memory = PlanningMemory()
    memory.clear()

    memory.record_success(
        intent_name="customer_reply",
        candidate=_candidate("candidate_customer"),
    )
    memory.record_success(
        intent_name="url_summary",
        candidate=_candidate("candidate_url"),
    )

    results = memory.retrieve(
        intent=detect_intent(text="Reply to customer"),
        context=None,
    )

    assert [item.candidate.id for item in results] == ["candidate_customer"]
    assert results[0].metadata["success_count"] == 1


def test_planning_memory_rolling_latency_average():
    memory = PlanningMemory()
    memory.clear()

    candidate = _candidate()

    memory.record_success(
        intent_name="customer_reply",
        candidate=candidate,
        latency_ms=100,
    )
    entry = memory.record_success(
        intent_name="customer_reply",
        candidate=candidate,
        latency_ms=300,
    )

    assert entry.success_count == 2
    assert entry.average_latency_ms == 200
