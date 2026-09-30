from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.domains.customer_service.repositories.omnichannel import OmnichannelRepository
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.schemas.conversations import ConversationCreate
from app.domains.customer_service.services.inbox import InboxService
from app.platform.events.publisher import PlatformEventPublisher


@pytest.mark.asyncio
async def test_omnichannel_message_received_event_updates_ticket_priority():
    user_id = uuid4()

    async with SessionLocal() as db:
        customer = await OmnichannelRepository(db).create_customer(
            user_id=user_id,
            name="Event Customer",
            email=f"{uuid4()}@example.com",
        )

        conversation = await InboxService(db).create_conversation(
            user_id=user_id,
            payload=ConversationCreate(
                customer_id=customer.id,
                channel="whatsapp",
                subject="Event driven damaged product",
            ),
        )

        ticket = await TicketRepository(db).get_by_conversation_id(
            conversation.id,
        )
        assert ticket is not None
        assert ticket.priority == "normal"

        result = await PlatformEventPublisher(db).publish(
            user_id=user_id,
            event_type="customer_service.omnichannel.message.received",
            source="customer_service.omnichannel",
            payload={
                "conversation_id": str(conversation.id),
                "message_id": str(uuid4()),
                "ticket_id": str(ticket.id),
                "customer_id": str(customer.id),
                "channel": "whatsapp",
                "external_account_id": "event-account-1",
                "external_thread_id": "event-thread-1",
                "external_message_id": "event-message-1",
                "body": "My product arrived damaged and I need urgent help",
            },
            dispatch=True,
        )

        assert result["handler_results"]
        assert result["handler_results"][0]["handled"] is True

        updated = await TicketRepository(db).get_by_conversation_id(
            conversation.id,
        )
        assert updated.priority == "urgent"
