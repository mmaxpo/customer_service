from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.inbox.schemas import (
    InboxEmailAddress,
    NormalizedInboundEmail,
)
from app.domains.customer_service.inbox.service import InboundEmailIngestService
from app.domains.customer_service.models import Conversation, ConversationMessage


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "match_method",
    ["external_thread", "in_reply_to", "references", "customer_subject"],
)
@pytest.mark.parametrize(
    "same_account",
    [True, False],
    ids=["same_account_threads", "different_accounts_stay_separate"],
)
async def test_email_thread_matching_respects_account(
    match_method, same_account
):
    user_id = uuid4()
    customer_email = f"{uuid4().hex}@example.com"
    original_message_id = f"original-{uuid4()}"
    reply_message_id = f"reply-{uuid4()}"
    thread_id = f"thread-{uuid4()}"
    first_account = "support-one@example.com"
    second_account = (
        first_account if same_account else "support-two@example.com"
    )

    first = NormalizedInboundEmail(
        provider="thread-isolation-test",
        external_account_id=first_account,
        external_message_id=original_message_id,
        external_thread_id=(
            thread_id if match_method == "external_thread" else None
        ),
        from_address=InboxEmailAddress(email=customer_email),
        to=[InboxEmailAddress(email=first_account)],
        subject="Original request",
        body_text="First support message",
    )

    second = NormalizedInboundEmail(
        provider="thread-isolation-test",
        external_account_id=second_account,
        external_message_id=reply_message_id,
        external_thread_id=(
            thread_id if match_method == "external_thread" else None
        ),
        in_reply_to=(
            original_message_id if match_method == "in_reply_to" else None
        ),
        references=(
            [original_message_id] if match_method == "references" else []
        ),
        from_address=InboxEmailAddress(email=customer_email),
        to=[InboxEmailAddress(email=second_account)],
        subject=(
            "Re: Original request"
            if match_method == "customer_subject"
            else "A different subject"
        ),
        body_text="Second support message",
    )

    async with SessionLocal() as db:
        first_result = await InboundEmailIngestService(db).ingest(
            user_id=user_id, email=first
        )

    async with SessionLocal() as db:
        second_result = await InboundEmailIngestService(db).ingest(
            user_id=user_id, email=second
        )

    # Inspect committed state through a fresh database session.
    async with SessionLocal() as db:
        conversations = list(
            (
                await db.scalars(
                    select(Conversation).where(
                        Conversation.user_id == user_id
                    )
                )
            ).all()
        )
        messages = list(
            (
                await db.scalars(
                    select(ConversationMessage)
                    .join(Conversation)
                    .where(Conversation.user_id == user_id)
                )
            ).all()
        )

        assert first_result.created_conversation is True
        assert first_result.message_id != second_result.message_id
        assert len(messages) == 2

        by_id = {str(message.id): message for message in messages}
        assert by_id[first_result.message_id].meta[
            "external_account_id"
        ] == first_account
        assert by_id[second_result.message_id].meta[
            "external_account_id"
        ] == second_account

        if same_account:
            assert second_result.created_conversation is False
            assert second_result.conversation_id == first_result.conversation_id
            assert len(conversations) == 1
        else:
            assert second_result.created_conversation is True
            assert second_result.conversation_id != first_result.conversation_id
            assert len(conversations) == 2

        assert by_id[first_result.message_id].conversation_id == UUID(
            first_result.conversation_id
        )
        assert by_id[second_result.message_id].conversation_id == UUID(
            second_result.conversation_id
        )
