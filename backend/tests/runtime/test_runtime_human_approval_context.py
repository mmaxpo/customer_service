from copy import deepcopy
from uuid import uuid4

import pytest

from app.core.session import get_db
from app.runtime.nodes.registry.builtins import (
    register_builtin_nodes,
)
from app.runtime.engine.context import RuntimeContext
from app.runtime.engine.executor import (
    execute_workflow_dag,
)
from app.workflow_operations.waits.service import (
    WorkflowWaitService,
)


def _dummy_request():
    class State:
        tools = None

    class Request:
        state = State()

    return Request()


def _workflow():
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
                "id": "extract_review_context",
                "data": {
                    "nodeType": "context.extract",
                    "source": "extras",
                    "path": "support_review",
                    "save_as": "support_review",
                },
            },
            {
                "id": "approval",
                "data": {
                    "nodeType": "human.approval",
                    "question": (
                        "Approve this customer-support "
                        "resolution plan?"
                    ),
                    "context_key": "support_review",
                    "context_payload_key": "context",
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
                "source": "trigger",
                "target": "extract_review_context",
            },
            {
                "source": "extract_review_context",
                "target": "approval",
            },
            {
                "source": "approval",
                "target": "response",
            },
        ],
    }


@pytest.mark.asyncio
async def test_human_approval_copies_context_into_durable_wait():
    register_builtin_nodes()
    user_id = uuid4()

    support_review = {
        "review_plan_id": "review-plan-123",
        "review_plan": {
            "order_ref": "#1003",
            "operations": [
                {
                    "operation_type": "partial_refund",
                    "item_id": "line-item-1",
                },
                {
                    "operation_type": "replacement",
                    "item_id": "line-item-2",
                },
                {
                    "operation_type": (
                        "replacement_address"
                    ),
                    "address": {
                        "address1": "123 Main Street",
                    },
                },
            ],
        },
    }

    expected_context = deepcopy(support_review)

    async for db in get_db():
        ctx = RuntimeContext(
            request=_dummy_request(),
            user_id=user_id,
            thread_id=uuid4(),
            db=db,
            extras={
                "support_review": support_review,
            },
        )

        result = await execute_workflow_dag(
            ctx=ctx,
            workflow=_workflow(),
            message="start",
        )

        assert result["meta"]["status"] == "paused"

        waits = await WorkflowWaitService(
            db
        ).list_for_user(
            user_id=user_id,
            status="waiting",
        )

        wait = next(
            item
            for item in waits
            if item.node_id == "approval"
        )

        assert wait.payload["context"] == (
            expected_context
        )
        assert wait.payload["context_key"] == (
            "support_review"
        )

        interrupt = (
            result["meta"]["final_state"]
            ["meta"]["interrupt"]
        )

        assert interrupt["context"] == (
            expected_context
        )
        assert interrupt["context_key"] == (
            "support_review"
        )
        assert interrupt["workflow_wait_id"] == str(
            wait.id
        )

        # The stored approval context must be an isolated
        # copy rather than the original mutable input.
        support_review["review_plan"]["order_ref"] = (
            "#CHANGED"
        )

        assert wait.payload["context"]["review_plan"][
            "order_ref"
        ] == "#1003"

        break


@pytest.mark.asyncio
async def test_human_approval_without_context_is_backward_compatible():
    register_builtin_nodes()
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
                "source": "trigger",
                "target": "approval",
            },
            {
                "source": "approval",
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

        assert result["meta"]["status"] == "paused"

        waits = await WorkflowWaitService(
            db
        ).list_for_user(
            user_id=user_id,
            status="waiting",
        )

        wait = next(
            item
            for item in waits
            if item.node_id == "approval"
        )

        assert "context" not in wait.payload
        assert "context_key" not in wait.payload

        break
