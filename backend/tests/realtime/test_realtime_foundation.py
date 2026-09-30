import asyncio
from uuid import uuid4

import pytest

from app.platform.realtime.codec import encode_sse_event
from app.platform.realtime.hub import RealtimeHub
from app.platform.realtime.publisher import RealtimePublisher
from app.platform.realtime.schemas import RealtimeEvent


@pytest.mark.asyncio
async def test_realtime_hub_delivers_only_to_matching_user_and_scope():
    hub = RealtimeHub()
    publisher = RealtimePublisher()
    publisher_module_hub = __import__(
        "app.platform.realtime.publisher", fromlist=["realtime_hub"]
    )

    original_hub = publisher_module_hub.realtime_hub
    publisher_module_hub.realtime_hub = hub

    try:
        user_a = uuid4()
        user_b = uuid4()

        conn_a = await hub.register(user_id=user_a, scope="customer_service")
        conn_b = await hub.register(user_id=user_b, scope="customer_service")
        conn_wrong_scope = await hub.register(user_id=user_a, scope="other")

        event = await publisher.publish(
            user_id=user_a,
            type="customer_service.message.created",
            scope="customer_service",
            entity_type="conversation",
            entity_id=uuid4(),
            payload={"preview": "hello"},
        )

        assert await asyncio.wait_for(conn_a.queue.get(), timeout=1) == event
        assert conn_b.queue.empty()
        assert conn_wrong_scope.queue.empty()
    finally:
        publisher_module_hub.realtime_hub = original_hub


def test_realtime_event_sse_encoding():
    event = RealtimeEvent(
        user_id=uuid4(),
        type="customer_service.message.created",
        scope="customer_service",
        entity_type="conversation",
        entity_id=uuid4(),
        payload={"preview": "hello"},
    )

    encoded = encode_sse_event(event)

    assert encoded.startswith("event: customer_service.message.created\\n")
    assert "\\ndata: " in encoded
    assert encoded.endswith("\\n\\n")
