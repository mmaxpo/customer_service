from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    Conversation,
    ConversationTag,
    Customer,
    CustomerServiceNotification,
    CustomerServiceProactiveIncident,
    Ticket,
)
from app.domains.customer_service.services.proactive_playbooks import (
    CustomerServiceProactivePlaybookService,
)
from app.identity import create_user
from app.models.schemas import UserCreate
from app.tenancy.schemas import WorkspaceCreate
from app.tenancy.service import WorkspaceService


@pytest.mark.asyncio
async def test_vip_playbook_is_durable_actionable_and_cooldown_idempotent():
    async with SessionLocal() as db:
        user = await create_user(
            UserCreate(
                email=f"proactive-{uuid4()}@example.com",
                password=f"Proactive-{uuid4()}",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        workspace, _ = await WorkspaceService(db).create_workspace(
            user_id=user.id,
            payload=WorkspaceCreate(name=f"Proactive {uuid4()}"),
        )
        customer = Customer(
            user_id=workspace.id,
            workspace_id=workspace.id,
            name="VIP Customer",
            email=f"vip-{uuid4()}@example.com",
            custom_fields={"vip_tier": "gold", "lifetime_value": "not-a-number"},
        )
        db.add(customer)
        await db.flush()
        conversation = Conversation(
            user_id=workspace.id,
            workspace_id=workspace.id,
            customer_id=customer.id,
            channel="website",
            subject="VIP needs help",
            status="open",
        )
        db.add(conversation)
        await db.flush()
        ticket = Ticket(
            user_id=workspace.id,
            workspace_id=workspace.id,
            conversation_id=conversation.id,
            title="VIP needs help",
            status="open",
            priority="normal",
        )
        db.add(ticket)
        await db.commit()

        service = CustomerServiceProactivePlaybookService(
            db, workspace_id=workspace.id
        )
        policies = await service.seed_defaults()
        first = await service.evaluate()
        second = await service.evaluate()

        incidents = list(
            await db.scalars(
                select(CustomerServiceProactiveIncident).where(
                    CustomerServiceProactiveIncident.workspace_id == workspace.id,
                    CustomerServiceProactiveIncident.signal == "vip_customer",
                )
            )
        )
        tag = await db.scalar(
            select(ConversationTag).where(
                ConversationTag.conversation_id == conversation.id,
                ConversationTag.name == "proactive:vip_customer",
            )
        )
        notification_count = int(
            await db.scalar(
                select(func.count(CustomerServiceNotification.id)).where(
                    CustomerServiceNotification.workspace_id == workspace.id,
                    CustomerServiceNotification.kind == "proactive_alert",
                )
            )
            or 0
        )
        await db.refresh(ticket)

        assert len(policies) == 6
        assert first["incidents_created"] == 1
        assert second["incidents_created"] == 0
        assert len(incidents) == 1
        assert incidents[0].action_taken["tagged"] is True
        assert ticket.priority.value == "urgent"
        assert tag is not None
        assert notification_count == 1
