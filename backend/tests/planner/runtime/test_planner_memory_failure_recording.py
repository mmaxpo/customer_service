from app.tcos.planner.memory import PlanningMemory
from app.tcos.planner.runtime import PlannerRuntime, PlanningStatus
from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.verification.models import (
    VerificationIssue,
    VerificationResult,
    VerificationSeverity,
)


class FakeVerificationEngine:
    def verify(self, candidate):
        return VerificationResult(
            passed=False,
            issues=[
                VerificationIssue(
                    code="missing_artifact_producer",
                    severity=VerificationSeverity.ERROR,
                    message="Missing summary producer",
                    location="planning_operation:send_response",
                    details={"artifact_id": "summary"},
                )
            ],
        )


def test_planner_runtime_records_failed_plan_to_memory(monkeypatch):
    import app.tcos.planner.runtime.engine as engine_module

    monkeypatch.setattr(engine_module, "VerificationEngine", FakeVerificationEngine)

    session = PlannerRuntime().plan_goal(goal="Summarize https://example.com")

    assert session.status == PlanningStatus.FAILED

    memory_event = next(e for e in session.events if e.type == "PlanningMemoryRecorded")

    assert memory_event.payload["outcome"] == "failure"
    assert (
        memory_event.payload["candidate_id"]
        == "generated_generic_url_summary"
    )

    retrieved = PlanningMemory().retrieve(
        intent=detect_intent(text="Summarize https://example.com"),
        context=None,
    )

    assert len(retrieved) == 1
    assert retrieved[0].metadata["success_count"] == 0
    assert retrieved[0].metadata["failure_count"] == 1
    assert retrieved[0].metadata["success_rate"] == 0.0
