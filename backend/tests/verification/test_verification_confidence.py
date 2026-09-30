from app.tcos.verification.confidence import calculate_verification_confidence
from app.tcos.verification.models import (
    VerificationIssue,
    VerificationResult,
    VerificationSeverity,
)


def test_verification_confidence_is_full_when_no_issues():
    result = VerificationResult(passed=True)

    confidence = calculate_verification_confidence(result)

    assert confidence.overall == 1.0
    assert confidence.error_count == 0
    assert confidence.warning_count == 0


def test_verification_confidence_penalizes_errors_and_warnings():
    result = VerificationResult(
        passed=False,
        issues=[
            VerificationIssue(
                code="error",
                severity=VerificationSeverity.ERROR,
                message="Error",
            ),
            VerificationIssue(
                code="warning",
                severity=VerificationSeverity.WARNING,
                message="Warning",
            ),
        ],
    )

    confidence = calculate_verification_confidence(result)

    assert confidence.error_count == 1
    assert confidence.warning_count == 1
    assert confidence.overall == 0.4


def test_verification_engine_attaches_confidence():
    from app.tcos.planner.runtime.intent import detect_intent
    from app.tcos.planner.runtime.planner import Planner
    from app.tcos.planner.runtime.planning_context import PlanningContext
    from app.tcos.verification import VerificationEngine

    goal = "Summarize https://example.com"

    candidate = Planner().plan(
        intent=detect_intent(text=goal),
        context=PlanningContext(
            user_message=goal,
        ),
    )

    result = VerificationEngine().verify(candidate)

    assert result.confidence["overall"] == 1.0
