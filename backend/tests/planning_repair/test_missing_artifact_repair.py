from app.tcos.planning_repair import RepairEngine, RepairStrategyType
from app.tcos.verification.models import (
    VerificationIssue,
    VerificationResult,
    VerificationSeverity,
)


def test_repair_engine_plans_missing_artifact_producer_repair():
    verification = VerificationResult(
        passed=False,
        issues=[
            VerificationIssue(
                code="missing_artifact_producer",
                severity=VerificationSeverity.ERROR,
                message="Missing summary producer",
                location="planning_operation:reply",
                details={"artifact_id": "summary"},
            )
        ],
    )

    result = RepairEngine().plan_repair(verification)

    assert result.repairable is True
    assert result.plan.strategy == RepairStrategyType.REPLAN
    assert result.plan.confidence == 0.85
    assert result.plan.actions[0]["type"] == "insert_missing_artifact_producer"
    assert result.plan.actions[0]["artifact_id"] == "summary"
