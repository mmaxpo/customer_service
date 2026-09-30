from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domains.customer_service.services.shopify_action_workflows import (
    ShopifyActionWorkflowService,
)
from app.platform.jobs.service import JobService


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action_type",
    [
        "shopify_refund",
        "shopify_cancel",
        "shopify_damaged_item",
        "shopify_track_order",
    ],
)
async def test_dispatch_key_is_stable_and_distinguishes_actions(
    monkeypatch, action_type
):
    enqueue = AsyncMock(
        return_value=SimpleNamespace(
            id=uuid4(),
            job_type="workflow.run",
            status="queued",
        )
    )
    monkeypatch.setattr(JobService, "enqueue", enqueue)

    owner_id = uuid4()
    conversation_id = uuid4()

    def make_action():
        return SimpleNamespace(
            id=uuid4(),
            conversation_id=conversation_id,
            action_type=action_type,
            title="Customer request",
            source="test",
            payload={"order_ref": "#1001"},
        )

    service = ShopifyActionWorkflowService(db=None)
    original = make_action()
    separate = make_action()

    for action in (original, original, separate):
        await service.start_action_workflow(
            user_id=owner_id,
            suggested_action=action,
            payload={},
        )

    calls = [call.kwargs for call in enqueue.await_args_list]
    assert len(calls) == 3
    assert all(call["user_id"] == owner_id for call in calls)

    keys = [call.get("idempotency_key") for call in calls]
    assert all(isinstance(key, str) and key.strip() for key in keys), (
        "Every suggested-action dispatch needs a nonempty idempotency key"
    )
    assert keys[0] == keys[1], (
        "Retrying the same suggested action must reuse its dispatch key"
    )
    assert keys[0] != keys[2], (
        "A separate suggested action must retain its own dispatch identity"
    )
