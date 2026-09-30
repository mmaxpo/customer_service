from uuid import uuid4

import pytest

from app.core.session import get_db
from app.runtime.engine.context import RuntimeContext
from app.runtime.engine.executor import execute_workflow_dag


def _dummy_request():
    class State:
        tools = None

    class Request:
        state = State()

    return Request()


@pytest.mark.asyncio
async def test_platform_job_enqueue_node_creates_job():
    user_id = uuid4()

    workflow = {
        "nodes": [
            {
                "id": "trigger",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "start",
                },
            },
            {
                "id": "enqueue",
                "data": {
                    "nodeType": "platform.job.enqueue",
                    "job_type": "test.echo",
                    "payload": {
                        "hello": "from workflow",
                    },
                    "save_as": "queued_job",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "queued_job",
                },
            },
        ],
        "edges": [
            {
                "id": "e1",
                "source": "trigger",
                "target": "enqueue",
            },
            {
                "id": "e2",
                "source": "enqueue",
                "target": "response",
            },
        ],
    }

    async for db in get_db():
        ctx = RuntimeContext(
            request=_dummy_request(),
            user_id=user_id,
            thread_id=uuid4(),
            db=db,
        )

        result = await execute_workflow_dag(
            ctx=ctx,
            workflow=workflow,
            message="start",
        )

        assert result["meta"]["status"] == "ok"

        queued_job = result["meta"]["final_state"]["vars"]["queued_job"]

        assert queued_job["job_type"] == "test.echo"
        assert queued_job["status"] == "queued"
        assert queued_job["job_id"]

        break
