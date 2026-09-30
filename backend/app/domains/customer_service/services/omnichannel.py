from __future__ import annotations

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.integrations.omnichannel.protocol import (
    NormalizedOutboundAttachment,
    NormalizedOutboundMessage,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)
from app.domains.customer_service.models import Customer, CustomerServiceAttachment
from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.repositories.omnichannel import OmnichannelRepository
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.schemas.conversations import (
    ConversationCreate,
    ConversationMessageCreate,
    SenderType,
)
from app.domains.customer_service.schemas.omnichannel import (
    ChannelConnectionCreate,
    OmnichannelDeliveryEvent,
    OmnichannelInboundMessage,
    OmnichannelOutboundMessage,
)
from app.domains.customer_service.services.customer_identity import (
    CustomerIdentityConflictError,
    CustomerIdentityEvidence,
    CustomerIdentityService,
)
from app.domains.customer_service.services.inbox import InboxService
from app.platform.events.publisher import PlatformEventPublisher
from app.platform.jobs.service import JobService
from app.domains.customer_service.workflows.omnichannel_job_types import (
    OMNICHANNEL_INBOUND_MEDIA_MATERIALIZE_JOB,
)
from app.tenancy.models import Workspace


class CustomerServiceOmnichannelService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.omnichannel_repo = OmnichannelRepository(db)
        self.conversation_repo = ConversationRepository(db)
        self.ticket_repo = TicketRepository(db)
        self.inbox_service = InboxService(db)

    async def list_connections(self, user_id):
        return await self.omnichannel_repo.list_connections(user_id=user_id)

    async def create_connection(self, *, user_id, payload: ChannelConnectionCreate):
        return await self.omnichannel_repo.create_connection(
            user_id=user_id,
            channel=payload.channel,
            external_account_id=payload.external_account_id,
            display_name=payload.display_name,
            config=payload.config,
        )

    async def ingest_inbound_message(
        self, *, user_id, payload: OmnichannelInboundMessage
    ):
        # Serialize duplicate provider deliveries for the same external message.
        # This prevents the classic check-then-insert race under concurrent webhooks.
        lock_key = (
            f"cs_omnichannel_message:"
            f"{user_id}:"
            f"{payload.channel}:"
            f"{payload.external_account_id}:"
            f"{payload.external_message_id}"
        )
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": lock_key},
        )

        existing_message_link = await self.omnichannel_repo.get_external_message(
            user_id=user_id,
            channel=payload.channel,
            external_account_id=payload.external_account_id,
            external_message_id=payload.external_message_id,
        )
        if existing_message_link is not None:
            ticket = await self.ticket_repo.get_by_conversation_id(
                existing_message_link.conversation_id
            )
            conversation = await self.conversation_repo.get_by_id(
                existing_message_link.conversation_id
            )
            return {
                "conversation_id": existing_message_link.conversation_id,
                "message_id": existing_message_link.message_id,
                "ticket_id": ticket.id if ticket is not None else None,
                "customer_id": conversation.customer_id
                if conversation is not None
                else None,
                "channel": payload.channel,
                "duplicate": True,
                "workflow": None,
            }

        external_conversation = await self.omnichannel_repo.get_external_conversation(
            user_id=user_id,
            channel=payload.channel,
            external_account_id=payload.external_account_id,
            external_thread_id=payload.external_thread_id,
        )

        if external_conversation is None:
            customer = await self._get_or_create_customer(
                user_id=user_id, payload=payload
            )
            conversation = await self.inbox_service.create_conversation(
                user_id=user_id,
                payload=ConversationCreate(
                    customer_id=customer.id,
                    channel=payload.channel,
                    subject=payload.subject or self._default_subject(payload),
                ),
            )
            await self.omnichannel_repo.link_external_conversation(
                user_id=user_id,
                conversation_id=conversation.id,
                customer_id=customer.id,
                channel=payload.channel,
                external_account_id=payload.external_account_id,
                external_thread_id=payload.external_thread_id,
                external_customer_id=payload.external_customer_id,
                meta=self._conversation_link_meta(payload),
            )
        else:
            conversation = await self.conversation_repo.get_by_id(
                external_conversation.conversation_id
            )
            if conversation is not None and conversation.merged_into_id is not None:
                conversation = await self.conversation_repo.get_by_id(
                    conversation.merged_into_id
                )
            customer = await self.db.get(Customer, external_conversation.customer_id)
            if conversation is None:
                raise ValueError(
                    "External conversation link points to a missing conversation"
                )
            if customer is None:
                customer = await self._get_or_create_customer(
                    user_id=user_id, payload=payload
                )

        message_meta = self._message_meta(payload)
        message = await self.inbox_service.add_message(
            conversation_id=conversation.id,
            payload=ConversationMessageCreate(
                sender_type=SenderType.CUSTOMER,
                body=payload.body,
                meta=message_meta,
            ),
        )

        merged_meta = dict(message.meta or {})
        merged_meta["omnichannel"] = message_meta["omnichannel"]

        if payload.meta:
            merged_meta.update(payload.meta)
        await self.conversation_repo.update_message_meta(
            message_id=message.id,
            meta=merged_meta,
        )

        external_message_link = await self.omnichannel_repo.link_external_message(
            user_id=user_id,
            conversation_id=conversation.id,
            message_id=message.id,
            channel=payload.channel,
            external_account_id=payload.external_account_id,
            external_thread_id=payload.external_thread_id,
            external_message_id=payload.external_message_id,
            direction="inbound",
            delivery_status="received",
            meta=message_meta,
        )

        if external_message_link.message_id != message.id:
            ticket = await self.ticket_repo.get_by_conversation_id(
                external_message_link.conversation_id
            )
            existing_conversation = await self.conversation_repo.get_by_id(
                external_message_link.conversation_id
            )
            return {
                "conversation_id": external_message_link.conversation_id,
                "message_id": external_message_link.message_id,
                "ticket_id": ticket.id if ticket is not None else None,
                "customer_id": (
                    existing_conversation.customer_id
                    if existing_conversation is not None
                    else None
                ),
                "channel": payload.channel,
                "duplicate": True,
                "workflow": None,
            }

        ticket = await self.ticket_repo.get_by_conversation_id(conversation.id)

        for media in payload.media:
            media_job_payload = {
                "user_id": str(user_id),
                "conversation_id": str(conversation.id),
                "message_id": str(message.id),
                "channel": payload.channel,
                "external_account_id": payload.external_account_id,
                "external_message_id": payload.external_message_id,
                "provider_media_id": media.provider_media_id,
                "media": media.model_dump(mode="json"),
            }

            await JobService(self.db).enqueue(
                user_id=user_id,
                job_type=OMNICHANNEL_INBOUND_MEDIA_MATERIALIZE_JOB,
                payload=jsonable_encoder(media_job_payload),
                max_attempts=3,
                idempotency_key=(
                    "customer-service-omnichannel-inbound-media:"
                    f"{payload.channel}:"
                    f"{payload.external_account_id}:"
                    f"{payload.external_message_id}:"
                    f"{media.provider_media_id}"
                ),
                commit=False,
            )

        await self._publish_event(
            user_id=user_id,
            event_type="customer_service.omnichannel.message.received",
            payload={
                "conversation_id": str(conversation.id),
                "message_id": str(message.id),
                "ticket_id": str(ticket.id) if ticket is not None else None,
                "customer_id": str(conversation.customer_id),
                "customer_email": payload.customer_email,
                "channel": payload.channel,
                "external_account_id": payload.external_account_id,
                "external_thread_id": payload.external_thread_id,
                "external_message_id": payload.external_message_id,
                "external_customer_id": payload.external_customer_id,
                "body": payload.body,
                "workflow": merged_meta.get("workflow"),
            },
        )

        return {
            "conversation_id": conversation.id,
            "message_id": message.id,
            "ticket_id": ticket.id if ticket is not None else None,
            "customer_id": conversation.customer_id,
            "channel": payload.channel,
            "duplicate": False,
            "workflow": merged_meta.get("workflow"),
        }

    def _delivery_status_rank(self, status: str | None) -> int:
        ranks = {
            "queued": 0,
            "sent": 1,
            "delivered": 2,
            "read": 3,
            "failed": 100,
        }
        return ranks.get(str(status or "").lower(), -1)

    def _max_delivery_status(self, current: str | None, incoming: str) -> str:
        current_s = str(current or "").lower()
        incoming_s = str(incoming or "").lower()

        if current_s == "failed":
            return current_s

        if incoming_s == "failed":
            return incoming_s

        if self._delivery_status_rank(incoming_s) >= self._delivery_status_rank(
            current_s
        ):
            return incoming_s

        return current_s or incoming_s

    async def apply_delivery_event(self, *, user_id, payload: OmnichannelDeliveryEvent):
        link = await self.omnichannel_repo.get_external_message(
            user_id=user_id,
            channel=payload.channel,
            external_account_id=payload.external_account_id,
            external_message_id=payload.external_message_id,
        )

        if link is None:
            raise HTTPException(status_code=404, detail="External message not found")

        meta = dict(link.meta or {})
        omnichannel_meta = dict(meta.get("omnichannel") or {})

        events = list(omnichannel_meta.get("delivery_events") or [])

        if payload.event_id and any(
            event.get("event_id") == payload.event_id for event in events
        ):
            final_status = str(
                omnichannel_meta.get("delivery_status")
                or link.delivery_status
                or payload.delivery_status
            ).lower()
        else:
            final_status = self._max_delivery_status(
                omnichannel_meta.get("delivery_status") or link.delivery_status,
                payload.delivery_status,
            )

            event_record = {
                "event_id": payload.event_id,
                "delivery_status": payload.delivery_status,
                "applied_delivery_status": final_status,
                "raw_payload": payload.raw_payload,
                "meta": payload.meta,
            }

            events.append(event_record)

            omnichannel_meta["delivery_status"] = final_status
            omnichannel_meta["delivery_events"] = events
            meta["omnichannel"] = omnichannel_meta

            updated = (
                await self.omnichannel_repo.update_external_message_delivery_status(
                    user_id=user_id,
                    channel=payload.channel,
                    external_account_id=payload.external_account_id,
                    external_message_id=payload.external_message_id,
                    delivery_status=final_status,
                    meta=meta,
                )
            )
            link = updated or link

        await self._publish_event(
            user_id=user_id,
            event_type="customer_service.omnichannel.delivery.updated",
            payload={
                "external_message_id": payload.external_message_id,
                "delivery_status": final_status,
                "updated": True,
                "channel": payload.channel,
                "external_account_id": payload.external_account_id,
                "conversation_id": str(link.conversation_id),
                "message_id": str(link.message_id),
            },
        )

        return {
            "external_message_id": payload.external_message_id,
            "delivery_status": final_status,
            "updated": True,
        }

    async def _get_or_create_customer(
        self,
        *,
        user_id,
        payload: OmnichannelInboundMessage,
    ):
        evidence: list[CustomerIdentityEvidence] = []

        customer_email = (
            str(payload.customer_email).strip().lower()
            if payload.customer_email
            else None
        )

        customer_phone = (
            str(payload.customer_phone).strip() if payload.customer_phone else None
        )

        if customer_email:
            evidence.append(
                CustomerIdentityEvidence(
                    identity_type="email",
                    value=customer_email,
                    namespace="global",
                    source="omnichannel",
                )
            )

        if customer_phone:
            evidence.append(
                CustomerIdentityEvidence(
                    identity_type="phone",
                    value=customer_phone,
                    namespace="global",
                    source="omnichannel",
                )
            )

        if payload.external_customer_id:
            evidence.append(
                CustomerIdentityEvidence(
                    identity_type="provider_customer",
                    value=str(payload.external_customer_id).strip(),
                    namespace=(f"{payload.channel}:{payload.external_account_id}"),
                    provider=payload.channel,
                    external_account_id=(payload.external_account_id),
                    source="omnichannel",
                )
            )

        # Preserve existing anonymous-message semantics.
        # Without stable identity evidence there is nothing safe
        # to resolve across conversations.
        if not evidence:
            return await self.omnichannel_repo.create_customer(
                user_id=user_id,
                name=payload.customer_name,
                email=None,
                phone=None,
            )

        workspace_id = await self.db.scalar(
            select(Workspace.id).where(Workspace.id == user_id)
        )

        try:
            return await CustomerIdentityService(self.db).resolve_or_create(
                user_id=user_id,
                workspace_id=workspace_id,
                evidence=evidence,
                name=payload.customer_name,
                email=customer_email,
                phone=customer_phone,
            )
        except CustomerIdentityConflictError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "customer_identity_conflict",
                    "message": (
                        "Customer identity evidence resolves to multiple customers."
                    ),
                    "customer_ids": sorted(
                        str(customer_id) for customer_id in exc.customer_ids
                    ),
                },
            ) from exc

    def _default_subject(self, payload: OmnichannelInboundMessage) -> str:
        channel = payload.channel.replace("_", " ").title()
        preview = " ".join(payload.body.split())[:72]
        return payload.subject or f"{channel} conversation: {preview}"

    def _conversation_link_meta(self, payload: OmnichannelInboundMessage) -> dict:
        return {
            "source": "omnichannel",
            "raw_payload": payload.raw_payload,
            "meta": payload.meta,
        }

    def _message_meta(self, payload: OmnichannelInboundMessage) -> dict:
        return {
            "omnichannel": {
                "channel": payload.channel,
                "external_account_id": payload.external_account_id,
                "external_thread_id": payload.external_thread_id,
                "external_message_id": payload.external_message_id,
                "external_customer_id": payload.external_customer_id,
                "occurred_at": payload.occurred_at.isoformat()
                if payload.occurred_at
                else None,
                "raw_payload": payload.raw_payload,
                "meta": payload.meta,
            }
        }

    async def enqueue_outbound_delivery(
        self,
        *,
        user_id,
        payload: OmnichannelOutboundMessage,
    ):
        conversation = await self.conversation_repo.get_detail(
            user_id=user_id,
            conversation_id=payload.conversation_id,
        )
        if conversation is None:
            raise ValueError("Conversation not found")

        external_conversation = (
            await self.omnichannel_repo.get_external_conversation_by_conversation_id(
                user_id=user_id,
                conversation_id=payload.conversation_id,
            )
        )

        external_account_id = (
            external_conversation.external_account_id
            if external_conversation is not None
            else "default"
        )
        external_thread_id = payload.external_thread_id or (
            external_conversation.external_thread_id
            if external_conversation is not None
            else str(payload.conversation_id)
        )

        job_payload = {
            "user_id": str(user_id),
            "conversation_id": str(payload.conversation_id),
            "channel": conversation.channel,
            "external_account_id": external_account_id,
            "external_thread_id": external_thread_id,
            "body": payload.body,
            "sender_type": payload.sender_type,
            "attachment_ids": [str(item.attachment_id) for item in payload.attachments],
            "idempotency_key": payload.idempotency_key,
            "meta": payload.meta,
        }

        job = await JobService(self.db).enqueue(
            job_type="customer_service.omnichannel.outbound.send",
            payload=jsonable_encoder(job_payload),
            user_id=user_id,
            max_attempts=3,
        )

        return {
            "job_id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "payload": job.payload,
        }

    async def send_outbound_message(
        self, *, user_id, payload: OmnichannelOutboundMessage
    ):
        conversation = await self.conversation_repo.get_detail(
            user_id=user_id,
            conversation_id=payload.conversation_id,
        )
        if conversation is None:
            raise ValueError("Conversation not found")

        external_conversation = (
            await self.omnichannel_repo.get_external_conversation_by_conversation_id(
                user_id=user_id,
                conversation_id=payload.conversation_id,
            )
        )
        connection = await self.omnichannel_repo.get_connection(
            user_id=user_id,
            channel=conversation.channel,
            external_account_id=(
                external_conversation.external_account_id
                if external_conversation is not None
                else "default"
            ),
        )

        external_account_id = (
            external_conversation.external_account_id
            if external_conversation is not None
            else (
                connection.external_account_id if connection is not None else "default"
            )
        )
        external_thread_id = payload.external_thread_id or (
            external_conversation.external_thread_id
            if external_conversation is not None
            else str(payload.conversation_id)
        )

        if payload.idempotency_key:
            lock_key = (
                f"cs_omnichannel_outbound:"
                f"{user_id}:"
                f"{conversation.channel}:"
                f"{external_account_id}:"
                f"{payload.idempotency_key}"
            )
            await self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )

            existing_by_key = (
                await self.omnichannel_repo.find_outbound_message_by_idempotency_key(
                    user_id=user_id,
                    channel=conversation.channel,
                    external_account_id=external_account_id,
                    idempotency_key=payload.idempotency_key,
                )
            )
            if existing_by_key is not None:
                return self._outbound_result_from_external_link(existing_by_key)

        attachment_rows = []
        if payload.attachments:
            attachment_rows = list(
                await self.db.scalars(
                    select(CustomerServiceAttachment).where(
                        CustomerServiceAttachment.id.in_([item.attachment_id for item in payload.attachments]),
                        CustomerServiceAttachment.workspace_id == user_id,
                        CustomerServiceAttachment.conversation_id == payload.conversation_id,
                        CustomerServiceAttachment.scan_status == "clean",
                        CustomerServiceAttachment.deleted_at.is_(None),
                    )
                )
            )
            if len(attachment_rows) != len(payload.attachments):
                raise ValueError("One or more attachments are unavailable")

        registry = get_omnichannel_provider_registry()
        adapter = registry.get(conversation.channel)
        provider_result = await adapter.send_message(
            NormalizedOutboundMessage(
                user_id=user_id,
                conversation_id=payload.conversation_id,
                channel=conversation.channel,
                external_account_id=external_account_id,
                external_thread_id=external_thread_id,
                body=payload.body,
                sender_type=payload.sender_type,
                attachments=[
                    NormalizedOutboundAttachment(
                        attachment_id=row.id,
                        filename=row.filename,
                        content_type=row.content_type,
                        size_bytes=row.size_bytes,
                    )
                    for row in attachment_rows
                ],
                idempotency_key=payload.idempotency_key,
                meta=payload.meta,
            )
        )

        existing_by_provider_id = await self.omnichannel_repo.get_external_message(
            user_id=user_id,
            channel=conversation.channel,
            external_account_id=external_account_id,
            external_message_id=provider_result.external_message_id,
        )
        if (
            existing_by_provider_id is not None
            and existing_by_provider_id.direction == "outbound"
        ):
            return self._outbound_result_from_external_link(existing_by_provider_id)

        message_meta = {
            "omnichannel": {
                "channel": conversation.channel,
                "external_account_id": external_account_id,
                "external_thread_id": external_thread_id,
                "external_message_id": provider_result.external_message_id,
                "direction": "outbound",
                "delivery_status": provider_result.delivery_status.value,
                "provider_response": provider_result.raw_response,
                "idempotency_key": payload.idempotency_key,
                "meta": payload.meta,
            }
        }

        message = await self.inbox_service.add_message(
            conversation_id=payload.conversation_id,
            payload=ConversationMessageCreate(
                sender_type=SenderType(payload.sender_type),
                body=payload.body,
                meta=message_meta,
            ),
        )

        merged_meta = dict(message.meta or {})
        merged_meta["omnichannel"] = message_meta["omnichannel"]
        await self.conversation_repo.update_message_meta(
            message_id=message.id,
            meta=merged_meta,
        )

        await self.omnichannel_repo.link_external_message(
            user_id=user_id,
            conversation_id=payload.conversation_id,
            message_id=message.id,
            channel=conversation.channel,
            external_account_id=external_account_id,
            external_thread_id=external_thread_id,
            external_message_id=provider_result.external_message_id,
            direction="outbound",
            delivery_status=provider_result.delivery_status.value,
            meta=merged_meta,
        )

        await self._publish_event(
            user_id=user_id,
            event_type="customer_service.omnichannel.message.sent",
            payload={
                "conversation_id": str(payload.conversation_id),
                "message_id": str(message.id),
                "external_message_id": provider_result.external_message_id,
                "channel": conversation.channel,
                "external_account_id": external_account_id,
                "external_thread_id": external_thread_id,
                "delivery_status": provider_result.delivery_status.value,
            },
        )

        return {
            "conversation_id": payload.conversation_id,
            "message_id": message.id,
            "external_message_id": provider_result.external_message_id,
            "channel": conversation.channel,
            "external_account_id": external_account_id,
            "external_thread_id": external_thread_id,
            "delivery_status": provider_result.delivery_status.value,
            "provider_response": provider_result.raw_response,
        }

    def _outbound_result_from_external_link(self, link):
        meta = link.meta or {}
        omnichannel = meta.get("omnichannel") or {}

        return {
            "conversation_id": link.conversation_id,
            "message_id": link.message_id,
            "external_message_id": link.external_message_id,
            "channel": link.channel,
            "external_account_id": link.external_account_id,
            "external_thread_id": link.external_thread_id,
            "delivery_status": link.delivery_status
            or omnichannel.get("delivery_status")
            or "sent",
            "provider_response": omnichannel.get("provider_response"),
        }

    async def _publish_event(
        self,
        *,
        user_id,
        event_type: str,
        payload: dict,
        meta: dict | None = None,
    ) -> None:
        await PlatformEventPublisher(self.db).publish(
            user_id=user_id,
            event_type=event_type,
            source="customer_service.omnichannel",
            payload=payload,
            meta=meta or {},
            dispatch=True,
        )

    async def commit(self) -> None:
        """
        Commit the current omnichannel application transaction.

        Transaction persistence remains a domain-service concern;
        HTTP adapters do not manipulate the AsyncSession directly.
        """
        await self.db.commit()
