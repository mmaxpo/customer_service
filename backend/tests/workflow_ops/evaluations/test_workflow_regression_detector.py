from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.workflow_operations.evaluations.regression import WorkflowRegressionDetector
from app.workflow_operations.evaluations.schemas import (
    WorkflowEvaluationCaseResult,
    WorkflowEvaluationResult,
)


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "regression@test.com"


def _evaluation_result(
    *, name: str, cases: list[tuple[str, bool]]
) -> WorkflowEvaluationResult:
    case_results = [
        WorkflowEvaluationCaseResult(
            name=case_name,
            passed=passed,
            score=1.0 if passed else 0.0,
            expected_status="ok",
            actual_status="ok" if passed else "error",
        )
        for case_name, passed in cases
    ]

    total = len(case_results)
    passed_count = sum(1 for case in case_results if case.passed)

    return WorkflowEvaluationResult(
        name=name,
        passed=passed_count == total,
        score=passed_count / total if total else 0.0,
        total_cases=total,
        passed_cases=passed_count,
        failed_cases=total - passed_count,
        cases=case_results,
    )


def test_regression_detector_detects_case_regression():
    baseline = _evaluation_result(
        name="baseline",
        cases=[
            ("refund", True),
            ("shipping", True),
        ],
    )

    candidate = _evaluation_result(
        name="candidate",
        cases=[
            ("refund", True),
            ("shipping", False),
        ],
    )

    result = WorkflowRegressionDetector().check(
        baseline=baseline,
        candidate=candidate,
    )

    assert result.regression_detected is True
    assert result.improved is False
    assert result.baseline_score == 1.0
    assert result.candidate_score == 0.5
    assert result.score_delta == -0.5
    assert len(result.regressed_cases) == 1
    assert result.regressed_cases[0].name == "shipping"


def test_regression_detector_detects_improvement():
    baseline = _evaluation_result(
        name="baseline",
        cases=[
            ("refund", False),
            ("shipping", True),
        ],
    )

    candidate = _evaluation_result(
        name="candidate",
        cases=[
            ("refund", True),
            ("shipping", True),
        ],
    )

    result = WorkflowRegressionDetector().check(
        baseline=baseline,
        candidate=candidate,
    )

    assert result.regression_detected is False
    assert result.improved is True
    assert len(result.improved_cases) == 1
    assert result.improved_cases[0].name == "refund"


@pytest.mark.asyncio
async def test_regression_check_endpoint():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        baseline = _evaluation_result(
            name="baseline",
            cases=[
                ("case-a", True),
            ],
        )

        candidate = _evaluation_result(
            name="candidate",
            cases=[
                ("case-a", False),
            ],
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/workflow-evaluations/regression/check",
                json={
                    "baseline": baseline.model_dump(),
                    "candidate": candidate.model_dump(),
                    "min_score_delta": 0.0,
                },
            )

            assert response.status_code == 200, response.text
            body = response.json()

            assert body["regression_detected"] is True
            assert body["candidate_score"] == 0.0
            assert body["baseline_score"] == 1.0
            assert body["regressed_cases"][0]["name"] == "case-a"

    finally:
        app.dependency_overrides.clear()
