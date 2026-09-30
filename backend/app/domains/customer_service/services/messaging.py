from __future__ import annotations

import asyncio
import hashlib
import html
import json
import uuid
from datetime import datetime, timezone

import resend
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.environment import is_production_environment
from app.domains.customer_service.inbox.schemas import (
    InboxAttachmentIn,
    InboxEmailAddress,
    NormalizedInboundEmail,
)
from app.domains.customer_service.inbox.service import InboundEmailIngestService
from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    CustomerServiceEmailIdentity,
    EmailWebhookReceipt,
)
from app.domains.customer_service.schemas.commercial import ReplySendRequest
from app.domains.customer_service.schemas.conversations import (
    ConversationMessageCreate,
    SenderType,
)
from app.domains.customer_service.services.inbox import InboxService
from app.domains.customer_service.services.signatures import resolve_reply_signature
from app.services.email_service import EmailType, send_email


class CustomerServiceMessagingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_reply(
        self,
        *,
        workspace_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        payload: ReplySendRequest,
    ) -> dict:
        conversation = await self.db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == workspace_id,
                Conversation.merged_into_id.is_(None),
            )
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        signature = await resolve_reply_signature(
            self.db,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
        )
        body = payload.body
        if signature and signature.strip() and not body.rstrip().endswith(signature.strip()):
            body = f"{body.rstrip()}\n\n{signature.strip()}"

        source_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"tajeran:{workspace_id}:{conversation_id}:{payload.idempotency_key}",
        )
        existing = await self.db.scalar(
            select(ConversationMessage).where(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.source_type == "commercial_reply",
                ConversationMessage.source_message_id == source_id,
            )
        )
        message = existing
        if message is None:
            message = await InboxService(self.db).add_message_for_user(
                user_id=workspace_id,
                conversation_id=conversation_id,
                payload=ConversationMessageCreate(
                    sender_type=SenderType.AGENT,
                    body=body,
                    source_type="commercial_reply",
                    source_message_id=source_id,
                    meta={
                        "actor_user_id": str(actor_user_id),
                        "delivery": {"status": "pending"},
                    },
                ),
            )

        delivery = dict((message.meta or {}).get("delivery") or {})
        if delivery.get("status") == "sent":
            return self._reply_result(message, idempotent_replay=True)

        if conversation.channel in {"chat", "website", "web"}:
            provider_result = {"id": str(message.id), "provider": "website_chat"}
        elif conversation.channel == "email":
            await self.db.refresh(conversation, attribute_names=["customer"])
            recipient = conversation.customer.email if conversation.customer else None
            if not recipient:
                raise HTTPException(
                    status_code=422, detail="Customer has no email address"
                )
            identity = await self.db.scalar(
                select(CustomerServiceEmailIdentity).where(
                    CustomerServiceEmailIdentity.workspace_id == workspace_id
                )
            )
            if is_production_environment() and (
                identity is None or identity.verification_status != "verified"
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Verify the merchant email sender before sending replies",
                )
            verified_identity = (
                identity
                if identity is not None and identity.verification_status == "verified"
                else None
            )
            provider_result = await asyncio.to_thread(
                send_email,
                EmailType.NOREPLY,
                recipient,
                f"Re: {conversation.subject or 'Your support request'}",
                f"<p>{html.escape(body).replace(chr(10), '<br>')}</p>",
                idempotency_key=payload.idempotency_key,
                from_address=(
                    f"{verified_identity.from_name} <{verified_identity.from_email}>"
                    if verified_identity
                    else None
                ),
                reply_to=verified_identity.reply_to if verified_identity else None,
            )
        else:
            raise HTTPException(
                status_code=422,
                detail=f"No real reply adapter for channel '{conversation.channel}'",
            )

        message.meta = {
            **(message.meta or {}),
            "delivery": {
                "status": "sent",
                "provider": conversation.channel,
                "provider_result": provider_result,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        await self.db.commit()
        await self.db.refresh(message)
        return self._reply_result(message, idempotent_replay=existing is not None)

    @staticmethod
    def _reply_result(message: ConversationMessage, *, idempotent_replay: bool) -> dict:
        return {
            "message_id": str(message.id),
            "delivery": (message.meta or {}).get("delivery") or {},
            "idempotent_replay": idempotent_replay,
        }

    async def ingest_resend_webhook(
        self,
        *,
        workspace_id: uuid.UUID,
        raw_body: bytes,
        svix_id: str,
        svix_timestamp: str,
        svix_signature: str,
    ) -> dict:
        secret = settings.INBOUND_EMAIL_WEBHOOK_SECRET
        if not secret:
            raise HTTPException(
                status_code=503, detail="Inbound email is not configured"
            )
        try:
            resend.Webhooks.verify(
                {
                    "payload": raw_body.decode("utf-8"),
                    "headers": {
                        "id": svix_id,
                        "timestamp": svix_timestamp,
                        "signature": svix_signature,
                    },
                    "webhook_secret": secret,
                }
            )
            event = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(
                status_code=401, detail="Invalid email webhook"
            ) from exc

        receipt = EmailWebhookReceipt(
            workspace_id=workspace_id,
            provider="resend",
            event_id=svix_id,
            payload_hash=hashlib.sha256(raw_body).hexdigest(),
        )
        self.db.add(receipt)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            return {"status": "duplicate", "event_id": svix_id}

        if event.get("type") != "email.received":
            receipt.status = "ignored"
            await self.db.commit()
            return {"status": "ignored", "event_id": svix_id}

        data = event.get("data") or {}
        sender = self._address(data.get("from"))
        recipients = [self._address(item) for item in (data.get("to") or [])]
        normalized = NormalizedInboundEmail(
            provider="resend",
            external_account_id=str(workspace_id),
            external_message_id=str(
                data.get("email_id") or data.get("message_id") or svix_id
            ),
            external_thread_id=data.get("thread_id"),
            from_address=sender,
            to=recipients,
            subject=data.get("subject"),
            body_text=data.get("text"),
            body_html=data.get("html"),
            in_reply_to=data.get("in_reply_to"),
            references=data.get("references") or [],
            attachments=[
                InboxAttachmentIn(
                    filename=item.get("filename") or "attachment",
                    content_type=item.get("content_type"),
                    size_bytes=item.get("size"),
                    provider_attachment_id=str(
                        item.get("id") or item.get("attachment_id") or ""
                    )
                    or None,
                )
                for item in (data.get("attachments") or [])
                if isinstance(item, dict)
            ],
            # Store provider identifiers, not a second copy of the full PII payload.
            raw_payload={
                "email_id": data.get("email_id"),
                "message_id": data.get("message_id"),
                "thread_id": data.get("thread_id"),
                "webhook_event_id": svix_id,
            },
        )
        result = await InboundEmailIngestService(self.db).ingest(
            user_id=workspace_id,
            email=normalized,
        )
        receipt.status = "processed"
        await self.db.commit()
        return {"status": "processed", "event_id": svix_id, "ingest": result}

    @staticmethod
    def _address(value) -> InboxEmailAddress:
        if isinstance(value, dict):
            return InboxEmailAddress(email=value.get("email"), name=value.get("name"))
        text = str(value or "").strip()
        if "<" in text and text.endswith(">"):
            name, email_value = text.rsplit("<", 1)
            return InboxEmailAddress(email=email_value[:-1].strip(), name=name.strip())
        return InboxEmailAddress(email=text)
