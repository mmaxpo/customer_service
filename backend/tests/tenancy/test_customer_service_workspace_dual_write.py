from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.core.session import SessionLocal
from app.domains.customer_service.models import Conversation, Customer, Ticket
from app.domains.customer_service.schemas.conversations import ConversationCreate
from app.domains.customer_service.schemas.customers import CustomerCreate
from app.domains.customer_service.services.customers import CustomerService
from app.domains.customer_service.services.inbox import InboxService
from app.identity import create_user
from app.models.models import User
from app.models.schemas import UserCreate
from app.tenancy.models import Workspace, WorkspaceMembership
from app.tenancy.repository import WorkspaceRepository


@pytest.mark.asyncio
async def test_core_customer_service_writes_inherit_personal_workspace():
    suffix = uuid4().hex
    email = f"workspace-dual-write-{suffix}@example.com"

    async with SessionLocal() as db:
        user = await create_user(
            UserCreate(
                email=email,
                password="Correct Horse Battery Staple 1!",
                full_name="Workspace Dual Write",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        workspace = await WorkspaceRepository(db).get_personal_workspace_for_user(
            user_id=user.id
        )
        assert workspace is not None

        customer = await CustomerService(db).create_customer(
            CustomerCreate(
                name="Workspace Customer",
                email=f"customer-{suffix}@example.com",
            ),
            user.id,
        )
        conversation = await InboxService(db).create_conversation(
            user.id,
            ConversationCreate(
                customer_id=customer.id,
                channel="chat",
                subject="Workspace propagation",
            ),
        )
        ticket = await db.scalar(
            select(Ticket).where(Ticket.conversation_id == conversation.id)
        )

        assert customer.workspace_id == workspace.id
        assert conversation.workspace_id == workspace.id
        assert ticket is not None
        assert ticket.workspace_id == workspace.id

        await db.execute(delete(Ticket).where(Ticket.user_id == user.id))
        await db.execute(delete(Conversation).where(Conversation.user_id == user.id))
        await db.execute(delete(Customer).where(Customer.user_id == user.id))
        await db.execute(
            delete(WorkspaceMembership).where(WorkspaceMembership.user_id == user.id)
        )
        await db.execute(
            delete(Workspace).where(Workspace.created_by_user_id == user.id)
        )
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()
