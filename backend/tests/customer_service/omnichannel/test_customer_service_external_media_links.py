from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    CustomerServiceAttachment,
    CustomerServiceExternalMediaLink,
)
from app.domains.customer_service.repositories.omnichannel import (
    OmnichannelRepository,
)
from app.domains.customer_service.services.commercial_operations import (
    CommercialOperationsService,
)
from app.domains.customer_service.models import (
    ConversationMessage,
    Customer,
    Conversation,
    MessageSenderType,
)
from app.identity import create_user
from app.models.schemas import UserCreate
from app.tenancy.schemas import WorkspaceCreate
from app.tenancy.service import WorkspaceService


@pytest.mark.asyncio
async def test_external_media_link_is_idempotent_and_attachment_can_flush(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "ATTACHMENT_STORAGE_ROOT",
        str(tmp_path),
    )

    conversation_id = uuid4()
    message_id = uuid4()
    attachment_id = uuid4()

    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=f"external-media-{uuid4()}@example.com",
                password=f"External-Media-{uuid4()}",
            ),
            db,
        )

        workspace, _ = await WorkspaceService(db).create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(name=f"External Media {uuid4()}"),
        )

        user_id = workspace.id

        customer = Customer(
            user_id=workspace.id,
            workspace_id=workspace.id,
            name="Media Customer",
        )
        db.add(customer)

        await db.flush()

        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            workspace_id=user_id,
            customer_id=customer.id,
            channel="generic",
            subject="Media inbound",
        )
        db.add(conversation)

        message = ConversationMessage(
            id=message_id,
            conversation_id=conversation_id,
            sender_type=MessageSenderType.CUSTOMER,
            body="",
        )
        db.add(message)

        await db.flush()

        service = CommercialOperationsService(
            db,
            workspace_id=user_id,
        )

        attachment = await service.store_attachment(
            conversation_id=conversation_id,
            message_id=message_id,
            attachment_id=attachment_id,
            filename="photo.jpg",
            content_type="image/jpeg",
            content=b"provider-media-content",
            commit=False,
        )

        assert attachment.id == attachment_id

        repo = OmnichannelRepository(db)

        first = await repo.link_external_media(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            attachment_id=attachment_id,
            channel="generic",
            external_account_id="account-1",
            external_message_id="message-1",
            provider_media_id="provider-media-1",
            meta={
                "filename": "photo.jpg",
            },
        )

        second = await repo.link_external_media(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            attachment_id=attachment_id,
            channel="generic",
            external_account_id="account-1",
            external_message_id="message-1",
            provider_media_id="provider-media-1",
            meta={
                "filename": "ignored-on-replay.jpg",
            },
        )

        assert first.id == second.id
        assert first.attachment_id == attachment_id

        await db.commit()

    async with SessionLocal() as db:
        stored_attachment = await db.get(
            CustomerServiceAttachment,
            attachment_id,
        )

        assert stored_attachment is not None
        assert stored_attachment.message_id == message_id

        links = list(
            (
                await db.scalars(
                    select(CustomerServiceExternalMediaLink).where(
                        CustomerServiceExternalMediaLink.user_id == user_id,
                        CustomerServiceExternalMediaLink.channel == "generic",
                        CustomerServiceExternalMediaLink.external_account_id
                        == "account-1",
                        CustomerServiceExternalMediaLink.external_message_id
                        == "message-1",
                        CustomerServiceExternalMediaLink.provider_media_id
                        == "provider-media-1",
                    )
                )
            ).all()
        )

        assert len(links) == 1
        assert links[0].attachment_id == attachment_id


@pytest.mark.asyncio
async def test_attachment_commit_false_does_not_commit_outer_transaction(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "ATTACHMENT_STORAGE_ROOT",
        str(tmp_path),
    )

    conversation_id = uuid4()
    message_id = uuid4()
    attachment_id = uuid4()

    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=f"external-media-rollback-{uuid4()}@example.com",
                password=f"External-Media-Rollback-{uuid4()}",
            ),
            db,
        )

        workspace, _ = await WorkspaceService(db).create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(name=f"External Media Rollback {uuid4()}"),
        )

        user_id = workspace.id

        customer = Customer(
            user_id=workspace.id,
            workspace_id=workspace.id,
            name="Rollback Customer",
        )
        db.add(customer)

        await db.flush()

        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            workspace_id=user_id,
            customer_id=customer.id,
            channel="generic",
        )
        db.add(conversation)

        db.add(
            ConversationMessage(
                id=message_id,
                conversation_id=conversation_id,
                sender_type=MessageSenderType.CUSTOMER,
                body="",
            )
        )

        await db.flush()

        service = CommercialOperationsService(
            db,
            workspace_id=user_id,
        )

        await service.store_attachment(
            conversation_id=conversation_id,
            message_id=message_id,
            attachment_id=attachment_id,
            filename="rollback.txt",
            content_type="text/plain",
            content=b"rollback-content",
            commit=False,
        )

        # If store_attachment() committed internally, this rollback
        # would not remove the canonical attachment row.
        await db.rollback()

    async with SessionLocal() as db:
        assert (
            await db.get(
                CustomerServiceAttachment,
                attachment_id,
            )
            is None
        )
