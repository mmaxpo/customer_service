from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domains.customer_service.services.shopify_action_workflows import (
    ShopifyActionWorkflowService,
)
from app.platform.jobs.service import JobService


def _make_enqueue_mock():
    return AsyncMock(
        return_value=SimpleNamespace(
            id=uuid4(),
            job_type="workflow.run",
            status="queued",
        )
    )


@pytest.mark.asyncio
async def test_cancel_action_routes_through_capability_invoke(monkeypatch):
    enqueue = _make_enqueue_mock()
    monkeypatch.setattr(JobService, "enqueue", enqueue)

    service = ShopifyActionWorkflowService(db=None)
    action = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        action_type="shopify_cancel",
        title="Customer request",
        source="test",
        payload={"order_ref": "#1001"},
    )

    await service.start_action_workflow(
        user_id=uuid4(),
        suggested_action=action,
        payload={},
    )

    call = enqueue.await_args_list[0]
    workflow = call.kwargs["payload"]["workflow"]

    shopify_action_node = next(
        node for node in workflow["nodes"] if node["id"] == "shopify_action"
    )
    data = shopify_action_node["data"]

    assert data["nodeType"] == "capability.invoke"
    assert data["config"]["capability_id"] == "ecommerce.orders.action"
    assert data["config"]["input_from"] == "vars"
    assert data["config"]["input_key"] == "order_ref"
    assert data["config"]["payload"]["action"] == "cancel"
    assert (
        data["config"]["payload"]["idempotency_key"]
        == "cs:shopify:cancel:#1001"
    )


@pytest.mark.asyncio
async def test_refund_action_still_uses_shopify_order_action_node(monkeypatch):
    enqueue = _make_enqueue_mock()
    monkeypatch.setattr(JobService, "enqueue", enqueue)

    service = ShopifyActionWorkflowService(db=None)
    action = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        action_type="shopify_refund",
        title="Customer request",
        source="test",
        payload={"order_ref": "#1002"},
    )

    await service.start_action_workflow(
        user_id=uuid4(),
        suggested_action=action,
        payload={},
    )

    call = enqueue.await_args_list[0]
    workflow = call.kwargs["payload"]["workflow"]

    shopify_action_node = next(
        node for node in workflow["nodes"] if node["id"] == "shopify_action"
    )
    data = shopify_action_node["data"]

    assert data["nodeType"] == "shopify.order_action"
    assert data["action"] == "refund"
