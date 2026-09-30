from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import get_db
from app.main import app
from app.api.auth import get_current_user
from app.workflow_operations.metrics.service import WorkflowMetricsService


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "metrics@test.com"


def _fake_result(status="ok", answer="DONE"):
    return {
        "answer": answer,
        "meta": {
            "status": status,
            "workflow_run_id": str(uuid4()),
            "elapsed_ms": 123,
            "events": [
                {"event": "run_start"},
                {"event": "node_start", "node_id": "trigger"},
                {"event": "node_end", "node_id": "trigger"},
                {"event": "node_start", "node_id": "response"},
                {"event": "node_end", "node_id": "response"},
                {"event": "run_end"},
            ],
            "final_state": {
                "errors": {},
            },
        },
    }


@pytest.mark.asyncio
async def test_workflow_metrics_records_and_summarizes_version():
    user_id = uuid4()
    definition_id = uuid4()

    async for db in get_db():
        service = WorkflowMetricsService(db)

        first = await service.record_from_workflow_result(
            user_id=user_id,
            workflow_definition_id=definition_id,
            workflow_version=1,
            result=_fake_result(status="ok"),
            metadata_json={"source": "test"},
        )

        second = await service.record_from_workflow_result(
            user_id=user_id,
            workflow_definition_id=definition_id,
            workflow_version=1,
            result=_fake_result(status="error"),
        )

        assert first["status"] == "ok"
        assert first["duration_ms"] == 123
        assert first["node_count"] == 2

        assert second["status"] == "error"

        summary = await service.summarize_version(
            user_id=user_id,
            workflow_definition_id=definition_id,
            workflow_version=1,
        )

        assert summary["run_count"] == 2
        assert summary["success_count"] == 1
        assert summary["failure_count"] == 1
        assert summary["success_rate"] == 0.5
        assert summary["avg_duration_ms"] == 123.0

        break


@pytest.mark.asyncio
async def test_workflow_metrics_empty_version_summary_returns_zero_counts():
    user_id = uuid4()

    async for db in get_db():
        summary = await WorkflowMetricsService(db).summarize_version(
            user_id=user_id,
            workflow_definition_id=uuid4(),
            workflow_version=999,
        )

        assert summary["run_count"] == 0
        assert summary["success_count"] == 0
        assert summary["failure_count"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["avg_duration_ms"] == 0.0
        assert summary["total_errors"] == 0
        assert summary["total_retries"] == 0
        assert summary["total_approvals"] == 0

        break


@pytest.mark.asyncio
async def test_workflow_metrics_endpoint_lists_and_summarizes():
    user = FakeUser()
    definition_id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async for db in get_db():
            service = WorkflowMetricsService(db)

            await service.record_from_workflow_result(
                user_id=user.id,
                workflow_definition_id=definition_id,
                workflow_version=2,
                result=_fake_result(status="ok"),
            )

            break

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            list_response = await client.get("/workflow-metrics/runs")

            assert list_response.status_code == 200, list_response.text
            assert list_response.json()

            summary_response = await client.get(
                f"/workflow-metrics/definitions/{definition_id}/versions/2/summary"
            )

            assert summary_response.status_code == 200, summary_response.text
            body = summary_response.json()

            assert body["run_count"] >= 1
            assert body["success_count"] >= 1
            assert body["success_rate"] > 0

    finally:
        app.dependency_overrides.clear()
