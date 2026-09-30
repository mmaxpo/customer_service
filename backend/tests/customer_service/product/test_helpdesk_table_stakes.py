from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    Customer,
    Ticket,
)
from app.domains.customer_service.schemas.helpdesk import (
    ConversationSnoozeRequest,
    ReplyDraftWrite,
    ReplySignatureWrite,
)
from app.domains.customer_service.services.helpdesk import (
    CustomerServiceHelpdeskService,
    CustomerServiceModerationService,
)
from app.identity import create_user
from app.models.schemas import UserCreate
from app.tenancy.schemas import WorkspaceCreate
from app.tenancy.service import WorkspaceService


async def helpdesk_context(db):
    user = await create_user(
        UserCreate(
            email=f"helpdesk-{uuid4()}@example.com",
            password=f"Helpdesk-{uuid4()}",
            terms_accepted=True,
            terms_version="v1",
            privacy_accepted=True,
            privacy_version="v1",
        ),
        db,
    )
    workspace, _ = await WorkspaceService(db).create_workspace(
        user_id=user.id, payload=WorkspaceCreate(name=f"Helpdesk {uuid4()}")
    )
    customer = Customer(
        user_id=workspace.id,
        workspace_id=workspace.id,
        name="Store Customer",
        email=f"customer-{uuid4()}@example.com",
    )
    db.add(customer)
    await db.flush()
    conversation = Conversation(
        user_id=workspace.id,
        workspace_id=workspace.id,
        customer_id=customer.id,
        channel="website",
        subject="Help needed",
        status="open",
    )
    db.add(conversation)
    await db.flush()
    db.add(
        Ticket(
            user_id=workspace.id,
            workspace_id=workspace.id,
            conversation_id=conversation.id,
            title="Help needed",
            status="open",
            priority="normal",
        )
    )
    await db.commit()
    return user, workspace, customer, conversation


@pytest.mark.asyncio
async def test_snooze_is_durable_and_older_wake_cannot_override_newer_snooze():
    async with SessionLocal() as db:
        user, workspace, _, conversation = await helpdesk_context(db)
        service = CustomerServiceHelpdeskService(
            db, workspace_id=workspace.id, actor_user_id=user.id
        )
        first = datetime.now(timezone.utc) + timedelta(hours=1)
        second = first + timedelta(hours=1)
        await service.snooze(
            conversation.id, ConversationSnoozeRequest(until=first, reason="Later")
        )
        row = await service.snooze(
            conversation.id, ConversationSnoozeRequest(until=second, reason="Tomorrow")
        )

        superseded = await service.wake(
            conversation.id, expected_until=first.isoformat()
        )

        assert superseded["status"] == "superseded"
        assert row.snoozed_until == second


@pytest.mark.asyncio
async def test_persisted_draft_version_and_server_side_signature():
    async with SessionLocal() as db:
        user, workspace, _, conversation = await helpdesk_context(db)
        service = CustomerServiceHelpdeskService(
            db, workspace_id=workspace.id, actor_user_id=user.id
        )
        await service.upsert_signature(
            user_id=None,
            payload=ReplySignatureWrite(
                name="Store signature", body="— The Store Support Team"
            ),
        )
        draft = await service.create_draft(
            conversation.id, ReplyDraftWrite(body="Your order is on the way.")
        )
        updated = await service.update_draft(
            draft.id,
            ReplyDraftWrite(
                body="Your order has shipped.", expected_version=draft.version
            ),
        )
        with pytest.raises(HTTPException) as conflict:
            await service.update_draft(
                draft.id,
                ReplyDraftWrite(body="Stale edit", expected_version=1),
            )
        sent = await service.send_draft(updated.id)
        message = await db.scalar(
            select(ConversationMessage).where(
                ConversationMessage.id == sent.sent_message_id
            )
        )

        assert conflict.value.status_code == 409
        assert sent.status == "sent"
        assert message.body.endswith("— The Store Support Team")


@pytest.mark.asyncio
async def test_phishing_is_quarantined_and_customer_custom_fields_are_scoped():
    async with SessionLocal() as db:
        user, workspace, customer, conversation = await helpdesk_context(db)
        service = CustomerServiceHelpdeskService(
            db, workspace_id=workspace.id, actor_user_id=user.id
        )
        assessment = await service.assess_inbound(
            conversation.id,
            "Urgent: verify your password at https://bad.example now",
        )
        updated_customer = await service.update_customer_custom_fields(
            customer.id, {"vip_tier": "gold", "lifetime_value": 2500}
        )

        assert CustomerServiceModerationService.classify("Normal order question")[
            "status"
        ] == "normal"
        assert assessment["status"] == "phishing"
        assert conversation.moderation_status == "phishing"
        assert updated_customer.custom_fields["vip_tier"] == "gold"
