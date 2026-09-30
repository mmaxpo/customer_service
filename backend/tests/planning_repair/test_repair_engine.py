from app.tcos.planning_repair import RepairEngine, RepairStrategyType
from app.tcos.verification.models import (
    VerificationIssue,
    VerificationResult,
    VerificationSeverity,
)


def test_repair_engine_returns_not_repairable_for_passed_verification():
    result = RepairEngine().plan_repair(VerificationResult(passed=True))

    assert result.repairable is False
    assert result.plan is None


def test_repair_engine_replans_missing_capability():
    verification = VerificationResult(
        passed=False,
        issues=[
            VerificationIssue(
                code="missing_capability",
                severity=VerificationSeverity.ERROR,
                message="Missing capability",
            )
        ],
    )

    result = RepairEngine().plan_repair(verification)

    assert result.repairable is True
    assert result.plan.strategy == RepairStrategyType.REPLAN
    assert result.plan.confidence == 0.8


def test_repair_engine_escalates_unknown_error():
    verification = VerificationResult(
        passed=False,
        issues=[
            VerificationIssue(
                code="unknown",
                severity=VerificationSeverity.ERROR,
                message="Unknown",
            )
        ],
    )

    result = RepairEngine().plan_repair(verification)

    assert result.repairable is True
    assert result.plan.strategy == RepairStrategyType.ESCALATE
