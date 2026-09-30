from __future__ import annotations

import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.inbox.schemas import (
    InboundEmailIngestResult,
    NormalizedInboundEmail,
)
from app.domains.customer_service.inbox.threading import EmailThreadingResolver
from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    ConversationStatus,
    Customer,
    MessageSenderType,
    Ticket,
)
from app.domains.customer_service.repositories.omnichannel import (
    OmnichannelRepository,
)
from app.domains.customer_service.services.customer_identity import (
    CustomerIdentityEvidence,
    CustomerIdentityService,
)
from app.tenancy.models import Workspace


logger = logging.getLogger(__name__)


class InboundEmailIngestService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.threading = EmailThreadingResolver(db)
        self.omnichannel_repo = OmnichannelRepository(db)

    async def ingest(
        self,
        *,
        user_id,
        email: NormalizedInboundEmail,
    ) -> InboundEmailIngestResult:
        lock_key = (
            f"cs_email_inbound:{user_id}:"
            f"{email.external_account_id}:"
            f"{email.external_message_id}"
        )

        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": lock_key},
        )

        existing = await self.omnichannel_repo.get_external_message(
            user_id=user_id,
            channel="email",
            external_account_id=email.external_account_id,
            external_message_id=email.external_message_id,
        )

        if existing is not None:
            return InboundEmailIngestResult(
                conversation_id=str(existing.conversation_id),
                message_id=str(existing.message_id),
                customer_email=str(email.from_address.email),
                created_conversation=False,
                provider=email.provider,
                external_message_id=email.external_message_id,
            )

        customer = await self._get_or_create_customer(
            user_id=user_id,
            email=email,
        )

        conversation = await self.threading.find_conversation(
            user_id=user_id,
            email=email,
        )
        if conversation is not None and conversation.merged_into_id is not None:
            conversation = await self.db.scalar(
                select(Conversation).where(
                    Conversation.id == conversation.merged_into_id,
                    Conversation.user_id == user_id,
                )
            )

        created_conversation = False

        if conversation is None:
            workspace_exists = await self.db.scalar(
                select(Workspace.id).where(Workspace.id == user_id)
            )
            if workspace_exists:
                from app.domains.customer_service.services.commercial_operations import (
                    CommercialOperationsService,
                )

                await CommercialOperationsService(
                    self.db, workspace_id=user_id
                ).require_monthly_conversation_quota()
            conversation = self._new_conversation(
                user_id=user_id,
                customer=customer,
                email=email,
            )
            self.db.add(conversation)
            await self.db.flush()
            created_conversation = True

        message = ConversationMessage(
            conversation_id=conversation.id,
            sender_type=MessageSenderType.CUSTOMER,
            body=email.body_text or email.body_html or "",
            meta={
                "provider": email.provider,
                "external_account_id": email.external_account_id,
                "external_message_id": email.external_message_id,
                "external_thread_id": email.external_thread_id,
                "in_reply_to": email.in_reply_to,
                "references": email.references,
                "from": email.from_address.model_dump(mode="json"),
                "to": [item.model_dump(mode="json") for item in email.to],
                "cc": [item.model_dump(mode="json") for item in email.cc],
                "bcc": [item.model_dump(mode="json") for item in email.bcc],
                "subject": email.subject,
                "body_html": email.body_html,
                "attachments": [
                    item.model_dump(mode="json") for item in email.attachments
                ],
                "raw_payload": email.raw_payload,
            },
        )

        self.db.add(message)
        await self.db.flush()

        if created_conversation:
            ticket = Ticket(
                user_id=user_id,
                workspace_id=customer.workspace_id,
                conversation_id=conversation.id,
                title=conversation.subject or "Inbound email",
                status="open",
                priority="normal",
            )
            self.db.add(ticket)
            await self.db.flush()
            from app.domains.customer_service.services.sla import SLAService

            await SLAService(self.db).create_targets_for_ticket(ticket=ticket)

        await self.omnichannel_repo.link_external_message(
            user_id=user_id,
            conversation_id=conversation.id,
            message_id=message.id,
            channel="email",
            external_account_id=email.external_account_id,
            external_thread_id=(email.external_thread_id or str(conversation.id)),
            external_message_id=email.external_message_id,
            direction="inbound",
            delivery_status="received",
            meta={
                "provider": email.provider,
                "source": "inbound_email",
            },
        )

        conversation.status = ConversationStatus.OPEN

        await self.db.commit()
        await self.db.refresh(conversation)
        await self.db.refresh(message)

        if await self.db.scalar(select(Workspace.id).where(Workspace.id == user_id)):
            try:
                from app.domains.customer_service.realtime.publisher import (
                    CustomerServiceRealtimePublisher,
                )
                from app.domains.customer_service.services.suggested_actions import (
                    SuggestedActionService,
                )
                from app.domains.customer_service.workflows.trigger_handlers import (
                    CustomerServiceWorkflowTriggerHandler,
                )

                await SuggestedActionService(self.db).generate(
                    user_id=user_id,
                    conversation_id=conversation.id,
                )
                workflow = await CustomerServiceWorkflowTriggerHandler(
                    self.db
                ).on_message_created(
                    user_id=user_id,
                    conversation_id=conversation.id,
                    body=message.body,
                )
                message.meta = {**(message.meta or {}), "workflow": workflow}
                await self.db.commit()
                await CustomerServiceRealtimePublisher().publish_message_created(
                    user_id=user_id,
                    conversation_id=conversation.id,
                    message_id=message.id,
                    sender_type="customer",
                    preview=message.body[:240],
                    payload={"source": "inbound_email", "workflow": workflow},
                )
            except Exception:
                # Email acceptance must not be rolled back because an optional
                # AI/workflow follow-up is temporarily unavailable.
                await self.db.rollback()
                logger.exception(
                    "customer_service.inbound_email_automation_failed",
                    extra={
                        "workspace_id": str(user_id),
                        "conversation_id": str(conversation.id),
                        "message_id": str(message.id),
                    },
                )

        return InboundEmailIngestResult(
            conversation_id=str(conversation.id),
            message_id=str(message.id),
            customer_email=str(email.from_address.email),
            created_conversation=created_conversation,
            provider=email.provider,
            external_message_id=email.external_message_id,
        )

    async def _get_or_create_customer(
        self,
        *,
        user_id,
        email: NormalizedInboundEmail,
    ) -> Customer:
        customer_email = str(email.from_address.email).strip().lower()

        workspace_id = await self.db.scalar(
            select(Workspace.id).where(Workspace.id == user_id)
        )

        return await CustomerIdentityService(self.db).resolve_or_create(
            user_id=user_id,
            workspace_id=workspace_id,
            evidence=[
                CustomerIdentityEvidence(
                    identity_type="email",
                    value=customer_email,
                    namespace="global",
                    provider=email.provider,
                    external_account_id=(email.external_account_id),
                    source="inbound_email",
                )
            ],
            name=email.from_address.name,
            email=customer_email,
        )

    def _new_conversation(
        self,
        *,
        user_id,
        customer: Customer,
        email: NormalizedInboundEmail,
    ) -> Conversation:
        subject = self.threading.normalize_subject(email.subject or "(no subject)")

        return Conversation(
            user_id=user_id,
            workspace_id=customer.workspace_id,
            customer_id=customer.id,
            channel="email",
            subject=subject,
            status=ConversationStatus.OPEN,
        )
