from uuid import uuid4

import pytest

from app.domains.customer_service.realtime import events
from app.domains.customer_service.realtime.publisher import (
    CustomerServiceRealtimePublisher,
)
from app.platform.realtime.hub import RealtimeHub


@pytest.mark.asyncio
async def test_customer_service_realtime_message_event(monkeypatch):
    hub = RealtimeHub()

    import app.platform.realtime.publisher as realtime_publisher_module

    monkeypatch.setattr(realtime_publisher_module, "realtime_hub", hub)

    user_id = uuid4()
    conversation_id = uuid4()
    message_id = uuid4()

    connection = await hub.register(user_id=user_id, scope="customer_service")

    await CustomerServiceRealtimePublisher().publish_message_created(
        user_id=user_id,
        conversation_id=conversation_id,
        message_id=message_id,
        sender_type="customer",
        preview="Where is my order?",
    )

    event = await connection.queue.get()

    assert event.type == events.MESSAGE_CREATED
    assert event.scope == "customer_service"
    assert event.user_id == user_id
    assert event.entity_id == conversation_id
    assert event.payload["conversation_id"] == str(conversation_id)
    assert event.payload["message_id"] == str(message_id)
    assert event.payload["sender_type"] == "customer"


@pytest.mark.asyncio
async def test_customer_service_realtime_ai_reply_event(monkeypatch):
    hub = RealtimeHub()

    import app.platform.realtime.publisher as realtime_publisher_module

    monkeypatch.setattr(realtime_publisher_module, "realtime_hub", hub)

    user_id = uuid4()
    connection = await hub.register(user_id=user_id, scope="customer_service")

    await CustomerServiceRealtimePublisher().publish_message_created(
        user_id=user_id,
        conversation_id=uuid4(),
        message_id=uuid4(),
        sender_type="ai",
        preview="I found your order.",
    )

    event = await connection.queue.get()

    assert event.type == events.AI_REPLY_CREATED


@pytest.mark.asyncio
async def test_customer_service_realtime_workflow_and_sla_events(monkeypatch):
    hub = RealtimeHub()

    import app.platform.realtime.publisher as realtime_publisher_module

    monkeypatch.setattr(realtime_publisher_module, "realtime_hub", hub)

    user_id = uuid4()
    conversation_id = uuid4()
    ticket_id = uuid4()

    connection = await hub.register(user_id=user_id, scope="customer_service")

    await CustomerServiceRealtimePublisher().publish_workflow_started(
        user_id=user_id,
        conversation_id=conversation_id,
        job_id=uuid4(),
        payload={"source": "test"},
    )

    workflow_event = await connection.queue.get()
    assert workflow_event.type == events.WORKFLOW_STARTED
    assert workflow_event.payload["conversation_id"] == str(conversation_id)

    await CustomerServiceRealtimePublisher().publish_sla_updated(
        user_id=user_id,
        ticket_id=ticket_id,
        conversation_id=conversation_id,
        status="breached",
    )

    sla_event = await connection.queue.get()
    assert sla_event.type == events.SLA_UPDATED
    assert sla_event.payload["ticket_id"] == str(ticket_id)
    assert sla_event.payload["status"] == "breached"


@pytest.mark.asyncio
async def test_customer_service_realtime_shopify_action_completed(monkeypatch):
    hub = RealtimeHub()

    import app.platform.realtime.publisher as realtime_publisher_module

    monkeypatch.setattr(realtime_publisher_module, "realtime_hub", hub)

    user_id = uuid4()
    connection = await hub.register(user_id=user_id, scope="customer_service")

    await CustomerServiceRealtimePublisher().publish_shopify_action_completed(
        user_id=user_id,
        order_ref="#1004",
        action="shipping_status",
        status="prepared",
    )

    event = await connection.queue.get()

    assert event.type == events.SHOPIFY_ACTION_COMPLETED
    assert event.payload["order_ref"] == "#1004"
    assert event.payload["action"] == "shipping_status"
    assert event.payload["status"] == "prepared"
