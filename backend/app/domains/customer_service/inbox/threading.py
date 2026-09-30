from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    Customer,
)
from app.domains.customer_service.inbox.schemas import NormalizedInboundEmail


class EmailThreadingResolver:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_conversation(
        self,
        *,
        user_id,
        email: NormalizedInboundEmail,
    ) -> Conversation | None:
        found = await self._find_by_external_thread(
            user_id=user_id,
            email=email,
        )
        if found:
            return found

        found = await self._find_by_reply_headers(
            user_id=user_id,
            email=email,
        )
        if found:
            return found

        return await self._find_by_customer_subject(
            user_id=user_id,
            email=email,
        )

    async def _find_by_external_thread(
        self,
        *,
        user_id,
        email: NormalizedInboundEmail,
    ) -> Conversation | None:
        if not email.external_thread_id:
            return None

        q = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.channel == "email",
                Conversation.status != "resolved",
                Conversation.messages.any(
                    and_(
                        ConversationMessage.meta["external_thread_id"].astext
                        == email.external_thread_id,
                        ConversationMessage.meta["external_account_id"].astext
                        == email.external_account_id,
                    )
                ),
            )
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )

        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def _find_by_reply_headers(
        self,
        *,
        user_id,
        email: NormalizedInboundEmail,
    ) -> Conversation | None:
        external_ids: list[str] = []

        if email.in_reply_to:
            external_ids.append(email.in_reply_to)

        external_ids.extend(email.references or [])

        if not external_ids:
            return None

        q = (
            select(ConversationMessage)
            .join(Conversation)
            .where(
                Conversation.user_id == user_id,
                ConversationMessage.meta["external_message_id"].astext.in_(
                    external_ids
                ),
                ConversationMessage.meta["external_account_id"].astext
                == email.external_account_id,
            )
            .order_by(ConversationMessage.created_at.desc())
            .limit(1)
        )

        result = await self.db.execute(q)
        message = result.scalar_one_or_none()

        if not message:
            return None

        q2 = select(Conversation).where(Conversation.id == message.conversation_id)
        result2 = await self.db.execute(q2)
        return result2.scalar_one_or_none()

    async def _find_by_customer_subject(
        self,
        *,
        user_id,
        email: NormalizedInboundEmail,
    ) -> Conversation | None:
        subject = self.normalize_subject(email.subject or "")
        customer_email = str(email.from_address.email)

        if not subject:
            return None

        q = (
            select(Conversation)
            .join(Customer)
            .where(
                Conversation.user_id == user_id,
                Conversation.channel == "email",
                Conversation.status != "resolved",
                Customer.email == customer_email,
                Conversation.subject == subject,
                Conversation.messages.any(
                    ConversationMessage.meta["external_account_id"].astext
                    == email.external_account_id
                ),
            )
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )

        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    def normalize_subject(self, subject: str) -> str:
        value = subject.strip()

        changed = True
        while changed:
            changed = False
            lower = value.lower()

            for prefix in ("re:", "fw:", "fwd:"):
                if lower.startswith(prefix):
                    value = value[len(prefix) :].strip()
                    changed = True
                    break

        return value
