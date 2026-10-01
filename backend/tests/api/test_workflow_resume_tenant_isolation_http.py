from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.main import app
from app.runtime.nodes.registry.builtins import (
    register_builtin_nodes,
)
from app.runtime.persistence import build_run_store


class _AllowSignups:
    async def increment(self, *args, **kwargs) -> int:
        return 0


@pytest.fixture(autouse=True)
def _no_signup_rate_limit(monkeypatch):
    # These tests sign up from one address; the limiter is covered elsewhere.
    from app.api import auth as auth_api

    monkeypatch.setattr(auth_api, "_signup_rate_store", _AllowSignups())


async def _create_authenticated_client():
    client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )

    email = f"workflow-resume-{uuid4()}@example.com"
    password = f"WorkflowResume-{uuid4()}"

    signup = await client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": password,
            "terms_accepted": True,
            "terms_version": "v1",
            "privacy_accepted": True,
            "privacy_version": "v1",
        },
    )

    assert signup.status_code == 201

    login = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login.status_code == 200

    # Sign-up no longer returns the account (it answers the same for new and
    # existing emails), so the id comes from the signed-in session.
    user_id = (await client.get("/auth/me")).json()["id"]

    return client, user_id


def _approval_workflow():
    return {
        "nodes": [
            {
                "id": "trigger",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "start",
                },
            },
            {
                "id": "approval",
                "data": {
                    "nodeType": "human.approval",
                    "question": "Approve?",
                    "save_as": "approved",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                },
            },
        ],
        "edges": [
            {
                "id": "e1",
                "source": "trigger",
                "target": "approval",
            },
            {
                "id": "e2",
                "source": "approval",
                "target": "response",
            },
        ],
    }


async def _persisted_run(run_id):
    async with SessionLocal() as db:
        store = build_run_store(db)

        row = await store.get_run_public(
            run_id=UUID(run_id),
        )

        assert row is not None

        return {
            "user_id": (str(row["user_id"]) if row.get("user_id") else None),
            "status": row["status"],
        }


@pytest.mark.asyncio
async def test_cross_user_cannot_resume_paused_workflow_run():
    register_builtin_nodes()

    owner, owner_id = await _create_authenticated_client()

    attacker, attacker_id = await _create_authenticated_client()

    assert owner_id != attacker_id

    try:
        started = await owner.post(
            "/workflows_route/run",
            json={
                "workflow": _approval_workflow(),
                "message": "private owner input",
                "strict": True,
            },
        )

        assert started.status_code == 200

        meta = started.json()["meta"]

        assert meta["status"] == "paused"

        run_id = meta["workflow_run_id"]

        before = await _persisted_run(run_id)

        assert before == {
            "user_id": owner_id,
            "status": "paused",
        }

        attacked = await attacker.post(
            "/workflows_route/resume",
            json={
                "workflow_run_id": run_id,
                "input": {
                    "approved": True,
                    "attacker": "must-not-apply",
                },
                "strict": True,
            },
        )

        assert attacked.status_code == 403
        assert attacked.json() == {
            "detail": "Forbidden",
        }

        after_attack = await _persisted_run(run_id)

        assert after_attack == before

        owner_resume = await owner.post(
            "/workflows_route/resume",
            json={
                "workflow_run_id": run_id,
                "input": {
                    "approved": True,
                },
                "strict": True,
            },
        )

        assert owner_resume.status_code == 200
        assert owner_resume.json()["meta"]["status"] == "ok"

        after_owner = await _persisted_run(run_id)

        assert after_owner["user_id"] == owner_id
        assert after_owner["status"] == "done"

    finally:
        await owner.aclose()
        await attacker.aclose()


@pytest.mark.asyncio
async def test_resume_unknown_run_returns_404():
    client, _ = await _create_authenticated_client()

    try:
        response = await client.post(
            "/workflows_route/resume",
            json={
                "workflow_run_id": str(uuid4()),
                "input": {
                    "approved": True,
                },
                "strict": True,
            },
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Run not found",
        }
    finally:
        await client.aclose()
