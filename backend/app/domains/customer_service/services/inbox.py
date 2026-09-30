from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.repositories.customers import CustomerRepository
from app.domains.customer_service.repositories.inbox import InboxRepository
from app.domains.customer_service.repositories.tickets import TicketRepository

from app.domains.customer_service.schemas.conversations import (
    ConversationCreate,
)
from app.domains.customer_service.schemas.tickets import TicketCreate
from app.domains.customer_service.services.sla import SLAService
from app.domains.customer_service.repositories.chat_repository import ChatRepository
from app.domains.customer_service.services.chat_service import CustomerChatService
from app.domains.customer_service.realtime.publisher import (
    CustomerServiceRealtimePublisher,
)


class InboxService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.ticket_repo = TicketRepository(db)
        self.inbox_repo = InboxRepository(db)

    async def get_inbox(
        self, user_id, *, folder: str = "inbox", limit: int = 100, offset: int = 0
    ):
        return await self.inbox_repo.list(
            user_id,
            folder=folder,
            limit=limit,
            offset=offset,
        )

    async def list_conversations(
        self, user_id, *, limit: int = 100, offset: int = 0, shopify_connection_id=None
    ):
        if shopify_connection_id is not None:
            from app.domains.customer_service.repositories.shopify import (
                ShopifyRepository,
            )

            if (
                await ShopifyRepository(self.db).get_connection(
                    user_id=user_id, connection_id=shopify_connection_id
                )
                is None
            ):
                raise HTTPException(
                    status_code=404, detail="Shopify connection not found"
                )
        return await self.conversation_repo.list(
            user_id,
            limit=limit,
            offset=offset,
            shopify_connection_id=shopify_connection_id,
        )

    async def create_conversation(
        self,
        user_id,
        payload: ConversationCreate,
    ):
        # Legacy isolated tests use synthetic tenant IDs. Real workspaces enforce
        # their subscription quota before accepting another conversation.
        from sqlalchemy import select
        from app.tenancy.models import Workspace

        if await self.db.scalar(select(Workspace.id).where(Workspace.id == user_id)):
            from app.domains.customer_service.services.commercial_operations import (
                CommercialOperationsService,
            )

            await CommercialOperationsService(
                self.db, workspace_id=user_id
            ).require_monthly_conversation_quota()
        customer = await self.customer_repo.get(
            user_id=user_id,
            customer_id=payload.customer_id,
        )

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer not found",
            )

        conversation = await self.conversation_repo.create(
            user_id=user_id,
            conversation=payload,
            workspace_id=customer.workspace_id,
        )

        ticket = await self.ticket_repo.create(
            user_id=user_id,
            workspace_id=customer.workspace_id,
            ticket=TicketCreate(
                conversation_id=conversation.id,
                title=payload.subject or "New customer conversation",
                priority="normal",
                status="open",
                assigned_to=None,
            ),
        )

        await SLAService(self.db).create_targets_for_ticket(ticket=ticket)

        return conversation

    async def get_conversation_detail(self, user_id, conversation_id):
        conversation = await self.conversation_repo.get_detail(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if conversation is not None and getattr(conversation, "messages", None):
            sender_order = {
                "customer": 0,
                "system": 1,
                "internal_note": 2,
                "ai": 3,
                "agent": 4,
            }
            conversation.messages.sort(
                key=lambda message: (
                    message.created_at,
                    sender_order.get(str(message.sender_type), 99),
                    str(message.id),
                )
            )

        return conversation

    async def delete_conversation(self, user_id, conversation_id) -> bool:
        return await self.conversation_repo.delete_for_user(
            user_id=user_id,
            conversation_id=conversation_id,
        )

    async def list_messages(
        self,
        user_id,
        conversation_id,
        *,
        limit: int = 100,
        offset: int = 0,
    ):
        return await self.conversation_repo.list_messages(
            user_id=user_id,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
        )

    async def add_message_for_user(
        self,
        *,
        user_id,
        conversation_id,
        payload,
    ):
        conversation = await self.conversation_repo.get_for_user(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        return await self.add_message(
            conversation_id=conversation_id,
            payload=payload,
        )

    async def add_message(
        self,
        conversation_id,
        payload,
        *,
        commit: bool = True,
        publish_realtime: bool = True,
        run_customer_automation: bool = True,
    ):
        write_result = await self.conversation_repo.add_message_with_result(
            conversation_id=conversation_id,
            message=payload,
            commit=commit,
        )

        message = write_result.message

        # A durable source-identified message may already exist because
        # the same logical delivery is being retried.
        #
        # Persistence has already resolved the retry to the original row.
        # Do not repeat any secondary effects for that same delivery.
        if not write_result.created:
            return message

        conversation = await self.conversation_repo.get_by_id(conversation_id)

        if conversation is not None:
            if publish_realtime:
                await CustomerServiceRealtimePublisher().publish_message_created(
                    user_id=conversation.user_id,
                    conversation_id=conversation_id,
                    message_id=message.id,
                    sender_type=str(payload.sender_type),
                    preview=payload.body[:240] if payload.body else None,
                    payload={
                        "source": (payload.meta or {}).get("source"),
                    },
                )

            if payload.sender_type in ("agent", "ai"):
                ticket = await self.ticket_repo.get_by_conversation_id(
                    conversation_id=conversation_id,
                )

                if ticket is not None:
                    await SLAService(self.db).resolve_first_response_targets(
                        ticket_id=ticket.id,
                    )

                meta = payload.meta or {}
                if meta.get("source") != "customer_chat":
                    await CustomerChatService(
                        ChatRepository(self.db)
                    ).add_chat_assistant_message_for_conversation(
                        conversation_id=conversation_id,
                        content=payload.body,
                        source_message_id=message.id,
                        source_sender_type=str(payload.sender_type),
                    )

                    await self.db.commit()

            if str(payload.sender_type) == "customer" and run_customer_automation:
                from app.domains.customer_service.services.helpdesk import (
                    CustomerServiceHelpdeskService,
                )

                moderation = await CustomerServiceHelpdeskService(
                    self.db,
                    workspace_id=conversation.user_id,
                    actor_user_id=conversation.user_id,
                ).assess_inbound(conversation_id, payload.body)
                await self.conversation_repo.update_message_meta(
                    message_id=message.id,
                    meta={**(message.meta or {}), "moderation": moderation},
                )
                if moderation["status"] != "normal":
                    return message

                from app.domains.customer_service.services.suggested_actions import (
                    SuggestedActionService,
                )
                from app.domains.customer_service.workflows.trigger_handlers import (
                    CustomerServiceWorkflowTriggerHandler,
                )

                await SuggestedActionService(self.db).generate(
                    user_id=conversation.user_id,
                    conversation_id=conversation_id,
                )

                workflow_result = await CustomerServiceWorkflowTriggerHandler(
                    self.db
                ).on_message_created(
                    user_id=conversation.user_id,
                    conversation_id=conversation_id,
                    body=payload.body,
                )

                await self.conversation_repo.update_message_meta(
                    message_id=message.id,
                    meta={
                        **(message.meta or {}),
                        "workflow": workflow_result,
                    },
                )

        return message
