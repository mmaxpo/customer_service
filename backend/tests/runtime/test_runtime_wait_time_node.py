from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.core.session import get_db
from app.runtime.nodes.registry.builtins import register_builtin_nodes
from app.runtime.engine.context import RuntimeContext
from app.runtime.engine.executor import execute_workflow_dag
from app.workflow_operations.waits.service import WorkflowWaitService


def _dummy_request():
    class State:
        tools = None

    class Request:
        state = State()

    return Request()


def _wait_time_workflow():
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
                "id": "wait",
                "data": {
                    "nodeType": "wait.time",
                    "seconds": 60,
                    "reason": "delay follow-up",
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
            {"id": "e1", "source": "trigger", "target": "wait"},
            {"id": "e2", "source": "wait", "target": "response"},
        ],
    }


@pytest.mark.asyncio
async def test_wait_time_node_creates_durable_time_wait():
    register_builtin_nodes()
    user_id = uuid4()

    async for db in get_db():
        ctx = RuntimeContext(
            request=_dummy_request(),
            user_id=user_id,
            thread_id=uuid4(),
            db=db,
        )

        result = await execute_workflow_dag(
            ctx=ctx,
            workflow=_wait_time_workflow(),
            message="start",
        )

        assert result["meta"]["status"] == "paused"

        waits = await WorkflowWaitService(db).list_for_user(
            user_id=user_id,
            status="waiting",
        )

        wait = next(item for item in waits if item.node_id == "wait")

        assert wait.wait_type == "time"
        assert wait.payload["seconds"] == 60
        assert wait.payload["reason"] == "delay follow-up"
        assert wait.expires_at is not None
        assert wait.expires_at > datetime.now(timezone.utc)

        interrupt = result["meta"]["final_state"]["meta"]["interrupt"]

        assert interrupt["kind"] == "time"
        assert interrupt["type"] == "workflow_wait"
        assert interrupt["wait_type"] == "time"
        assert interrupt["workflow_wait_id"] == str(wait.id)

        break
