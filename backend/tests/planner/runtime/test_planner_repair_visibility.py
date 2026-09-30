from app.tcos.planner.runtime import PlannerRuntime, PlanningStatus
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


def test_planner_runtime_exposes_missing_artifact_repair_action(monkeypatch):
    import app.tcos.planner.runtime.engine as engine_module

    monkeypatch.setattr(engine_module, "VerificationEngine", FakeVerificationEngine)

    session = PlannerRuntime().plan_goal(goal="Summarize https://example.com")

    assert session.status == PlanningStatus.FAILED
    assert session.metrics["repairable"] is True
    assert session.metrics["repair_action_count"] == 1
    assert session.metrics["repair_action_types"] == [
        "insert_missing_artifact_producer"
    ]
    assert session.metrics["repair_artifact_ids"] == ["summary"]

    repair_event = next(
        event for event in session.events if event.type == "RepairPlanned"
    )

    assert repair_event.payload["action_count"] == 1
    assert repair_event.payload["action_types"] == ["insert_missing_artifact_producer"]
    assert repair_event.payload["artifact_ids"] == ["summary"]

    assert session.repair_result["plan"]["actions"][0]["artifact_id"] == "summary"
