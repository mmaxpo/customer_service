from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.domains.customer_service.integrations.omnichannel.errors import (
    OmnichannelProviderError,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)
from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    Customer,
    CustomerServiceAttachment,
    CustomerServiceExternalMediaLink,
    MessageSenderType,
)
from app.domains.customer_service.repositories.omnichannel import (
    OmnichannelRepository,
)
from app.domains.customer_service.workflows.omnichannel_jobs import (
    materialize_omnichannel_inbound_media_job,
)
from app.identity import create_user
from app.models.schemas import UserCreate
from app.tenancy.schemas import WorkspaceCreate
from app.tenancy.service import WorkspaceService


class _Job:
    def __init__(
        self,
        *,
        user_id,
    ):
        self.user_id = user_id
        self.attempts = 1
        self.max_attempts = 3


class _Ctx:
    def __init__(
        self,
        *,
        db,
        user_id,
    ):
        self.db = db
        self.job = _Job(
            user_id=user_id,
        )
        self.worker_id = "media-security-test"
        self.retryable = True


async def _create_product_graph(
    db,
    *,
    label: str,
    channel: str,
):
    owner = await create_user(
        UserCreate(
            email=f"media-security-{label}-{uuid4()}@example.com",
            password=f"Media-Security-{label}-{uuid4()}",
            terms_accepted=True,
            terms_version="v1",
            privacy_accepted=True,
            privacy_version="v1",
        ),
        db,
    )

    workspace, _ = await WorkspaceService(db).create_workspace(
        user_id=owner.id,
        payload=WorkspaceCreate(name=f"Media Security {label} {uuid4()}"),
    )

    customer = Customer(
        user_id=workspace.id,
        workspace_id=workspace.id,
        name=f"{label} Customer",
    )
    db.add(customer)
    await db.flush()

    conversation = Conversation(
        user_id=workspace.id,
        workspace_id=workspace.id,
        customer_id=customer.id,
        channel=channel,
        subject=f"{label} media security",
        status="open",
    )
    db.add(conversation)
    await db.flush()

    message = ConversationMessage(
        conversation_id=conversation.id,
        sender_type=MessageSenderType.CUSTOMER,
        body="",
    )
    db.add(message)
    await db.flush()

    return (
        owner,
        workspace,
        customer,
        conversation,
        message,
    )


def _payload(
    *,
    user_id,
    conversation_id,
    message_id,
    channel,
    external_account_id,
    external_message_id,
    provider_media_id="media-1",
    nested_provider_media_id=None,
):
    nested_provider_media_id = (
        nested_provider_media_id
        if nested_provider_media_id is not None
        else provider_media_id
    )

    return {
        "user_id": str(user_id),
        "conversation_id": str(conversation_id),
        "message_id": str(message_id),
        "channel": channel,
        "external_account_id": external_account_id,
        "external_message_id": external_message_id,
        "provider_media_id": provider_media_id,
        "media": {
            "provider_media_id": nested_provider_media_id,
            "filename": "attack.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 6,
            "metadata": {},
        },
    }


@pytest.mark.asyncio
async def test_inbound_media_tenant_and_identity_tampering_is_terminal_without_fetch(
    monkeypatch,
):
    from app.domains.customer_service.workflows import (
        omnichannel_jobs as jobs_module,
    )

    channel = f"media-security-{uuid4().hex}"

    account_a = "account-a"
    account_missing_connection = "account-no-connection"

    thread_a = "thread-a"

    external_message_a = "message-a"
    external_message_no_connection = "message-no-connection"

    fetch_calls = 0

    class MustNotFetchProvider:
        def __init__(self):
            self.channel = channel

        async def fetch_media(
            self,
            *,
            media,
            connection,
        ):
            nonlocal fetch_calls

            fetch_calls += 1

            raise AssertionError("tampered media job reached provider fetch")

    registry = get_omnichannel_provider_registry()

    test_adapters = dict(registry._adapters)
    test_adapters[channel] = MustNotFetchProvider()
    monkeypatch.setattr(registry, "_adapters", test_adapters)

    monkeypatch.setattr(
        jobs_module,
        "register_default_omnichannel_providers",
        lambda: None,
    )

    async with SessionLocal() as setup_db:
        (
            _owner_a,
            workspace_a,
            _customer_a,
            conversation_a,
            message_a,
        ) = await _create_product_graph(
            setup_db,
            label="A",
            channel=channel,
        )

        (
            _owner_b,
            workspace_b,
            _customer_b,
            conversation_b,
            message_b,
        ) = await _create_product_graph(
            setup_db,
            label="B",
            channel=channel,
        )

        repo = OmnichannelRepository(setup_db)

        await repo.create_connection(
            user_id=workspace_a.id,
            channel=channel,
            external_account_id=account_a,
            config={},
        )

        await repo.create_connection(
            user_id=workspace_b.id,
            channel=channel,
            external_account_id=account_a,
            config={},
        )

        await repo.link_external_message(
            user_id=workspace_a.id,
            conversation_id=conversation_a.id,
            message_id=message_a.id,
            channel=channel,
            external_account_id=account_a,
            external_thread_id=thread_a,
            external_message_id=external_message_a,
            direction="inbound",
        )

        # Same tenant and valid canonical graph, but deliberately
        # no ChannelConnection for this external account.
        await repo.link_external_message(
            user_id=workspace_a.id,
            conversation_id=conversation_a.id,
            message_id=message_a.id,
            channel=channel,
            external_account_id=account_missing_connection,
            external_thread_id="thread-no-connection",
            external_message_id=external_message_no_connection,
            direction="inbound",
        )

        await setup_db.commit()

        tenant_a = workspace_a.id
        tenant_b = workspace_b.id

        conversation_a_id = conversation_a.id
        conversation_b_id = conversation_b.id

        message_a_id = message_a.id
        message_b_id = message_b.id

    async def attack(
        *,
        payload,
        expected_code,
    ):
        nonlocal fetch_calls

        before_fetch_calls = fetch_calls

        async with SessionLocal() as db:
            ctx = _Ctx(
                db=db,
                user_id=tenant_a,
            )

            with pytest.raises(OmnichannelProviderError) as captured:
                await materialize_omnichannel_inbound_media_job(
                    payload,
                    ctx,
                )

            assert captured.value.code == expected_code
            assert ctx.retryable is False

            # Explicitly close the failed application transaction
            # and release its advisory transaction lock.
            await db.rollback()

        assert fetch_calls == before_fetch_calls

    # 1. Payload attempts to switch tenant and use tenant B's
    # canonical conversation/message. ctx.job.user_id must remain
    # authoritative as tenant A.
    await attack(
        payload=_payload(
            user_id=tenant_b,
            conversation_id=conversation_b_id,
            message_id=message_b_id,
            channel=channel,
            external_account_id=account_a,
            external_message_id=external_message_a,
        ),
        expected_code="external_message_mismatch",
    )

    # 2. Foreign conversation with otherwise valid tenant-A
    # external provider identity.
    await attack(
        payload=_payload(
            user_id=tenant_a,
            conversation_id=conversation_b_id,
            message_id=message_a_id,
            channel=channel,
            external_account_id=account_a,
            external_message_id=external_message_a,
        ),
        expected_code="external_message_mismatch",
    )

    # 3. Foreign message with tenant-A conversation.
    await attack(
        payload=_payload(
            user_id=tenant_a,
            conversation_id=conversation_a_id,
            message_id=message_b_id,
            channel=channel,
            external_account_id=account_a,
            external_message_id=external_message_a,
        ),
        expected_code="external_message_mismatch",
    )

    # 4. Wrong provider account cannot discover tenant A's
    # durable external-message identity.
    await attack(
        payload=_payload(
            user_id=tenant_a,
            conversation_id=conversation_a_id,
            message_id=message_a_id,
            channel=channel,
            external_account_id="attacker-account",
            external_message_id=external_message_a,
        ),
        expected_code="external_message_mismatch",
    )

    # 5. Wrong external message cannot be redirected onto the
    # legitimate canonical message.
    await attack(
        payload=_payload(
            user_id=tenant_a,
            conversation_id=conversation_a_id,
            message_id=message_a_id,
            channel=channel,
            external_account_id=account_a,
            external_message_id="attacker-message",
        ),
        expected_code="external_message_mismatch",
    )

    # 6. Top-level and nested provider-media identities must
    # agree before any database/provider side effect.
    await attack(
        payload=_payload(
            user_id=tenant_a,
            conversation_id=conversation_a_id,
            message_id=message_a_id,
            channel=channel,
            external_account_id=account_a,
            external_message_id=external_message_a,
            provider_media_id="media-top-level",
            nested_provider_media_id="media-tampered",
        ),
        expected_code="media_identity_mismatch",
    )

    # 7. Durable external-message identity exists, but its
    # provider account has no tenant-scoped connection.
    await attack(
        payload=_payload(
            user_id=tenant_a,
            conversation_id=conversation_a_id,
            message_id=message_a_id,
            channel=channel,
            external_account_id=account_missing_connection,
            external_message_id=external_message_no_connection,
        ),
        expected_code="channel_connection_missing",
    )

    assert fetch_calls == 0

    async with SessionLocal() as verify_db:
        tenant_a_attachment_count = await verify_db.scalar(
            select(func.count(CustomerServiceAttachment.id)).where(
                CustomerServiceAttachment.workspace_id == tenant_a
            )
        )

        tenant_b_attachment_count = await verify_db.scalar(
            select(func.count(CustomerServiceAttachment.id)).where(
                CustomerServiceAttachment.workspace_id == tenant_b
            )
        )

        media_link_count = await verify_db.scalar(
            select(func.count(CustomerServiceExternalMediaLink.id)).where(
                CustomerServiceExternalMediaLink.channel == channel
            )
        )

        assert tenant_a_attachment_count == 0
        assert tenant_b_attachment_count == 0
        assert media_link_count == 0
