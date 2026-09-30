from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.audit_logs import AuditLogRepository
from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.schemas.conversations import (
    ConversationMessageCreate,
    SenderType,
)
from app.domains.customer_service.services.notifications import NotificationService


class InternalNoteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversations = ConversationRepository(db)
        self.audit = AuditLogRepository(db)

    async def add_note(self, *, user_id, actor_id, conversation_id, payload):
        conversation = await self.conversations.get_detail(
            user_id=user_id, conversation_id=conversation_id
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        meta = payload.meta or {}
        meta["internal"] = True
        meta["author_id"] = str(actor_id)
        note = await self.conversations.add_message(
            conversation_id=conversation_id,
            message=ConversationMessageCreate(
                sender_type=SenderType.INTERNAL_NOTE, body=payload.body, meta=meta
            ),
        )
        await self.audit.create(
            user_id=user_id,
            actor_id=actor_id,
            entity_type="conversation",
            entity_id=conversation_id,
            action="internal_note.created",
            message="Internal note created",
            meta={"message_id": str(note.id)},
        )
        for mentioned_user_id in meta.get("mentions") or []:
            await NotificationService(self.db).create_if_uuid(
                workspace_id=user_id,
                recipient_user_id=mentioned_user_id,
                kind="mention",
                entity_type="conversation",
                entity_id=conversation_id,
                payload={"message_id": str(note.id), "mentioned_by": str(actor_id)},
            )
        return note
