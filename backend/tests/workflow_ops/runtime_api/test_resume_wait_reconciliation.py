from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.api import workflows as runtime_runs
from app.core.session import SessionLocal
from app.runtime.engine.persistence.postgres import PostgresRunStore


class FakeUser:
    def __init__(self):
        self.id = uuid4()


async def _seed_run(
    *,
    user_id,
    workflow_run_id: str,
    status: str,
):
    async with SessionLocal() as db:
        await PostgresRunStore(db).create_run(
            run_id=workflow_run_id,
            user_id=user_id,
            thread_id=uuid4(),
            workflow={
                "nodes": [],
                "edges": [],
            },
            state={
                "workflow_run_id": workflow_run_id,
                "status": status,
                "vars": {},
                "results": {},
                "errors": {},
                "meta": {
                    "status": status,
                    "user_id": str(user_id),
                },
            },
            status=status,
            extra={},
        )


async def _create_wait(
    client: AsyncClient,
    *,
    workflow_run_id: str,
) -> dict:
    response = await client.post(
        "/workflow-waits",
        json={
            "workflow_run_id": workflow_run_id,
            "node_id": "approval-1",
            "wait_type": "approval",
            "payload": {"question": "Approve?"},
        },
    )
    assert response.status_code == 200

    wait = response.json()
    assert wait["status"] == "waiting"
    return wait


async def _get_waits(
    client: AsyncClient,
    *,
    workflow_run_id: str,
) -> list[dict]:
    response = await client.get(
        "/workflow-waits",
        params={"workflow_run_id": workflow_run_id},
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_successful_synchronous_resume_resolves_outstanding_wait(monkeypatch):
    user = FakeUser()
    workflow_run_id = str(uuid4())

    await _seed_run(
        user_id=user.id,
        workflow_run_id=workflow_run_id,
        status="paused",
    )

    app.dependency_overrides[get_current_user] = lambda: user

    async def fake_execute_workflow_dag(**kwargs):
        return {
            "meta": {
                "status": "ok",
                "workflow_run_id": workflow_run_id,
            }
        }

    monkeypatch.setattr(
        runtime_runs,
        "execute_workflow_dag",
        fake_execute_workflow_dag,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await _create_wait(
                client,
                workflow_run_id=workflow_run_id,
            )

            response = await client.post(
                "/workflows_route/resume",
                json={
                    "workflow_run_id": workflow_run_id,
                    "input": {"approved": True},
                },
            )

            assert response.status_code == 200
            assert response.json()["meta"]["status"] == "ok"

            waits = await _get_waits(
                client,
                workflow_run_id=workflow_run_id,
            )

            reconciled = next(item for item in waits if item["id"] == created["id"])
            assert reconciled["status"] == "resolved"
            assert reconciled["resolution"]["approved"] is True
            assert reconciled["resolved_at"] is not None

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_duplicate_resume_of_done_run_reconciles_stale_wait(monkeypatch):
    user = FakeUser()
    workflow_run_id = str(uuid4())

    await _seed_run(
        user_id=user.id,
        workflow_run_id=workflow_run_id,
        status="done",
    )

    app.dependency_overrides[get_current_user] = lambda: user

    async def fake_execute_workflow_dag(**kwargs):
        return {
            "meta": {
                "status": "error",
                "error": "run_not_paused",
                "current_status": "done",
                "workflow_run_id": workflow_run_id,
            }
        }

    monkeypatch.setattr(
        runtime_runs,
        "execute_workflow_dag",
        fake_execute_workflow_dag,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await _create_wait(
                client,
                workflow_run_id=workflow_run_id,
            )

            response = await client.post(
                "/workflows_route/resume",
                json={
                    "workflow_run_id": workflow_run_id,
                    "input": {"approved": True},
                },
            )

            assert response.status_code == 200

            meta = response.json()["meta"]
            assert meta["error"] == "run_not_paused"
            assert meta["current_status"] == "done"

            waits = await _get_waits(
                client,
                workflow_run_id=workflow_run_id,
            )

            reconciled = next(item for item in waits if item["id"] == created["id"])
            assert reconciled["status"] == "resolved"
            assert reconciled["resolution"]["approved"] is True
            assert reconciled["resolved_at"] is not None

    finally:
        app.dependency_overrides.pop(get_current_user, None)
