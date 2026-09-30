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
                    "question": "Approve refund?",
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
            {"id": "e1", "source": "trigger", "target": "approval"},
            {"id": "e2", "source": "approval", "target": "response"},
        ],
    }


@pytest.mark.asyncio
async def test_human_approval_creates_durable_workflow_wait():
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
            workflow=_approval_workflow(),
            message="start",
        )

        assert result["meta"]["status"] == "paused"

        waits = await WorkflowWaitService(db).list_for_user(
            user_id=user_id,
            status="waiting",
        )

        wait = next(item for item in waits if item.node_id == "approval")

        assert wait.wait_type == "approval"
        assert wait.node_id == "approval"
        assert wait.payload["question"] == "Approve refund?"

        interrupt = result["meta"]["final_state"]["meta"]["interrupt"]

        assert interrupt["kind"] == "approval"
        assert interrupt["question"] == "Approve refund?"
        assert interrupt["type"] == "workflow_wait"
        assert interrupt["wait_type"] == "approval"
        assert interrupt["workflow_wait_id"] == str(wait.id)

        break
