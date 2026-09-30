from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.core.session import get_db
from app.runtime.nodes.registry.builtins import register_builtin_nodes
from app.workflow_operations.evaluations.schemas import (
    WorkflowEvaluationCase,
    WorkflowEvaluationRequest,
)
from app.workflow_operations.evaluations.service import WorkflowEvaluationService


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "eval@test.com"


def _workflow(answer="EVAL_OK"):
    return {
        "nodes": [
            {
                "id": "trigger",
                "data": {"nodeType": "trigger.message", "input": "start"},
            },
            {
                "id": "set_result",
                "data": {"nodeType": "set.variable", "key": "result", "value": answer},
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "result",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger", "target": "set_result"},
            {"id": "e2", "source": "set_result", "target": "response"},
        ],
    }


@pytest.mark.asyncio
async def test_workflow_evaluation_service_scores_cases():
    register_builtin_nodes()
    user_id = uuid4()

    async for db in get_db():
        result = await WorkflowEvaluationService(db).run_evaluation(
            user_id=user_id,
            request=WorkflowEvaluationRequest(
                name="basic-eval",
                cases=[
                    WorkflowEvaluationCase(
                        name="passes",
                        workflow=_workflow("EVAL_OK"),
                        message="start",
                        expected_answer="EVAL_OK",
                        expected_status="ok",
                    ),
                    WorkflowEvaluationCase(
                        name="fails",
                        workflow=_workflow("WRONG"),
                        message="start",
                        expected_answer="EXPECTED",
                        expected_status="ok",
                    ),
                ],
            ),
        )

        assert result.total_cases == 2
        assert result.passed_cases == 1
        assert result.failed_cases == 1
        assert result.score == 0.5
        assert result.passed is False
        assert result.cases[0].passed is True
        assert result.cases[1].passed is False

        break


@pytest.mark.asyncio
async def test_workflow_evaluation_endpoint_runs_cases():
    register_builtin_nodes()

    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/workflow-evaluations/run",
                json={
                    "name": "endpoint-eval",
                    "cases": [
                        {
                            "name": "passes",
                            "workflow": _workflow("API_EVAL_OK"),
                            "message": "start",
                            "expected_answer": "API_EVAL_OK",
                            "expected_status": "ok",
                        }
                    ],
                },
            )

            assert response.status_code == 200, response.text
            body = response.json()

            assert body["name"] == "endpoint-eval"
            assert body["passed"] is True
            assert body["score"] == 1.0
            assert body["total_cases"] == 1
            assert body["cases"][0]["passed"] is True

    finally:
        app.dependency_overrides.clear()
