from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.schemas.tickets import TicketUpdate
from app.domains.customer_service.workflows.message_classifier import (
    CustomerServiceMessageClassifier,
)
from app.domains.customer_service.workflows.workflow_mapper import (
    CustomerServiceWorkflowMapper,
)


class CustomerServiceWorkflowTriggerHandler:
    def __init__(self, db: AsyncSession):
        self.ticket_repo = TicketRepository(db)
        self.classifier = CustomerServiceMessageClassifier()
        self.mapper = CustomerServiceWorkflowMapper()

    async def on_message_created(
        self,
        *,
        user_id,
        conversation_id,
        body: str,
    ):
        classification = self.classifier.classify(body)
        action = self.mapper.map_intent(classification.intent)

        tickets = await self.ticket_repo.list(user_id)
        ticket = next(
            (
                item
                for item in tickets
                if str(item.conversation_id) == str(conversation_id)
            ),
            None,
        )

        if ticket is not None:
            await self.ticket_repo.update(
                user_id=user_id,
                ticket_id=ticket.id,
                payload=TicketUpdate(priority=action.ticket_priority),
            )

        return {
            "classification": classification.model_dump(),
            "action": action.model_dump(),
        }
