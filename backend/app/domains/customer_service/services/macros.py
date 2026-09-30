from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.audit_logs import AuditLogRepository
from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.repositories.macros import MacroRepository
from app.domains.customer_service.schemas.conversations import (
    ConversationMessageCreate,
    SenderType,
)
from app.domains.customer_service.services.sla import SLAService
from app.domains.customer_service.repositories.tickets import TicketRepository


class MacroService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MacroRepository(db)
        self.audit = AuditLogRepository(db)

    async def create(self, *, user_id, actor_id, payload):
        macro = await self.repo.create(user_id=user_id, payload=payload)
        await self.audit.create(
            user_id=user_id,
            actor_id=actor_id,
            entity_type="macro",
            entity_id=macro.id,
            action="macro.created",
            message=f"Macro created: {macro.name}",
        )
        return macro

    async def list(self, *, user_id, active_only: bool = True):
        return await self.repo.list(user_id=user_id, active_only=active_only)

    async def update(self, *, user_id, actor_id, macro_id, payload):
        macro = await self.repo.update(
            user_id=user_id, macro_id=macro_id, payload=payload
        )
        if macro is None:
            raise HTTPException(status_code=404, detail="Macro not found")
        await self.audit.create(
            user_id=user_id,
            actor_id=actor_id,
            entity_type="macro",
            entity_id=macro.id,
            action="macro.updated",
            message=f"Macro updated: {macro.name}",
        )
        return macro

    async def apply_to_conversation(
        self, *, user_id, actor_id, macro_id, conversation_id
    ):
        macro = await self.repo.get(user_id=user_id, macro_id=macro_id)
        if macro is None or not macro.is_active:
            raise HTTPException(status_code=404, detail="Macro not found")
        conversation = await ConversationRepository(self.db).get_detail(
            user_id=user_id, conversation_id=conversation_id
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        message = await ConversationRepository(self.db).add_message(
            conversation_id=conversation_id,
            message=ConversationMessageCreate(
                sender_type=SenderType.AGENT,
                body=macro.body,
                meta={"macro_id": str(macro.id), "macro_name": macro.name},
            ),
        )
        ticket = await TicketRepository(self.db).get_by_conversation_id(
            conversation_id=conversation_id,
        )

        if ticket is not None:
            await SLAService(self.db).resolve_first_response_targets(
                ticket_id=ticket.id,
            )
        await self.audit.create(
            user_id=user_id,
            actor_id=actor_id,
            entity_type="conversation",
            entity_id=conversation_id,
            action="macro.applied",
            message=f"Macro applied: {macro.name}",
            meta={"macro_id": str(macro.id), "message_id": str(message.id)},
        )
        return message
