import uuid
import pytest
import httpx
from app.main import app
from app.api.auth import get_current_user


# ---- fake user object compatible with your code ----
class FakeUser:
    def __init__(self, user_id: uuid.UUID):
        self.id = user_id


@pytest.mark.asyncio
async def test_pg_pause_list_events_resume_attempts():
    user_id = uuid.uuid4()

    # override auth dependency
    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    wf = {
        "nodes": [
            {"id": "t1", "data": {"nodeType": "trigger.message", "input": "start"}},
            {
                "id": "h1",
                "data": {
                    "nodeType": "human.approval",
                    "question": "Approve?",
                    "save_as": "approved",
                },
            },
            {
                "id": "s1",
                "data": {"nodeType": "set.variable", "key": "result", "value": "OK"},
            },
            {"id": "r1", "data": {"nodeType": "response"}},
        ],
        "edges": [
            {"id": "e1", "source": "t1", "target": "h1"},
            {"id": "e2", "source": "h1", "target": "s1"},
            {"id": "e3", "source": "s1", "target": "r1"},
        ],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1) start run -> paused
        r1 = await client.post(
            "/workflows_route/run", json={"workflow": wf, "message": ""}
        )
        assert r1.status_code == 200
        body1 = r1.json()
        assert body1["meta"]["status"] == "paused"
        run_id = body1["meta"]["workflow_run_id"]
        assert run_id

        # 2) list paused -> run present + interrupt exists
        rlist = await client.get(
            "/workflows_route/runs", params={"status": "paused", "limit": 20}
        )
        assert rlist.status_code == 200
        items = rlist.json()["items"]
        assert any(x["workflow_run_id"] == run_id for x in items)
        found = next(x for x in items if x["workflow_run_id"] == run_id)
        assert found["status"] == "paused"
        assert found["interrupt"] is not None

        # 3) events -> attempt 1 exists
        rev1 = await client.get(
            f"/workflows_route/runs/{run_id}/events", params={"limit": 200}
        )
        assert rev1.status_code == 200
        events1 = rev1.json()["events"]
        attempts1 = sorted(
            set((e.get("event") or {}).get("run_attempt") for e in events1)
        )
        assert 1 in attempts1

        # 4) resume -> ok
        r2 = await client.post(
            "/workflows_route/resume",
            json={"workflow_run_id": run_id, "input": {"approved": True}},
        )
        assert r2.status_code == 200
        body2 = r2.json()
        assert body2["meta"]["status"] == "ok"

        # 5) events -> attempt 2 exists
        rev2 = await client.get(
            f"/workflows_route/runs/{run_id}/events", params={"limit": 200}
        )
        assert rev2.status_code == 200
        events2 = rev2.json()["events"]
        attempts2 = sorted(
            set((e.get("event") or {}).get("run_attempt") for e in events2)
        )
        assert 1 in attempts2 and 2 in attempts2

    # cleanup override
    app.dependency_overrides.pop(get_current_user, None)
