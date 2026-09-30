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
from app.workflow_operations.quality.schemas import (
    WorkflowDeploymentGateRequest,
    WorkflowQualityInput,
)
from app.workflow_operations.quality.service import WorkflowQualityService


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "quality@test.com"


def _eval_result(*, name: str, passed_cases: int, total_cases: int):
    cases = []

    for i in range(total_cases):
        passed = i < passed_cases
        cases.append(
            WorkflowEvaluationCaseResult(
                name=f"case-{i}",
                passed=passed,
                score=1.0 if passed else 0.0,
                expected_status="ok",
                actual_status="ok" if passed else "error",
            )
        )

    score = passed_cases / total_cases if total_cases else 0.0

    return WorkflowEvaluationResult(
        name=name,
        passed=passed_cases == total_cases,
        score=score,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=total_cases - passed_cases,
        cases=cases,
    )


def test_workflow_quality_scores_good_workflow():
    evaluation = _eval_result(
        name="good",
        passed_cases=10,
        total_cases=10,
    )

    result = WorkflowQualityService().score(
        WorkflowQualityInput(
            evaluation=evaluation,
            metrics_summary={
                "run_count": 10,
                "success_rate": 1.0,
                "total_errors": 0,
            },
        )
    )

    assert result.score >= 0.95
    assert result.grade == "A"
    assert result.passed is True


def test_workflow_quality_blocks_regression():
    baseline = _eval_result(
        name="baseline",
        passed_cases=2,
        total_cases=2,
    )
    candidate = _eval_result(
        name="candidate",
        passed_cases=1,
        total_cases=2,
    )

    regression = WorkflowRegressionDetector().check(
        baseline=baseline,
        candidate=candidate,
    )

    gate = WorkflowQualityService().deployment_gate(
        WorkflowDeploymentGateRequest(
            quality=WorkflowQualityInput(
                evaluation=candidate,
                regression=regression,
                metrics_summary={
                    "run_count": 5,
                    "success_rate": 0.8,
                    "total_errors": 1,
                },
            ),
            min_score=0.8,
            block_on_regression=True,
        )
    )

    assert gate.allowed is False
    assert "regression_detected" in gate.blocked_reasons
    assert gate.score.score < 0.8


@pytest.mark.asyncio
async def test_workflow_quality_endpoint_scores():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        evaluation = _eval_result(
            name="api-good",
            passed_cases=1,
            total_cases=1,
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/workflow-quality/score",
                json={
                    "evaluation": evaluation.model_dump(),
                    "metrics_summary": {
                        "run_count": 1,
                        "success_rate": 1.0,
                        "total_errors": 0,
                    },
                },
            )

            assert response.status_code == 200, response.text
            body = response.json()

            assert body["score"] >= 0.95
            assert body["passed"] is True

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_workflow_deployment_gate_blocks_empty_quality_evidence():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            score_response = await client.post(
                "/workflow-quality/score",
                json={},
            )

            assert score_response.status_code == 200, score_response.text
            assert score_response.json()["score"] == 1.0
            assert score_response.json()["passed"] is True

            gate_response = await client.post(
                "/workflow-quality/deployment-gate",
                json={
                    "quality": {},
                },
            )

            assert gate_response.status_code == 200, gate_response.text

            body = gate_response.json()

            assert body["allowed"] is False
            assert body["score"]["score"] == 1.0
            assert body["blocked_reasons"] == ["quality_evidence_missing"]

    finally:
        app.dependency_overrides.clear()
