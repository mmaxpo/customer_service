from app.domains.customer_service.repositories.ticket_assignment import (
    TicketAssignmentRepository,
)
from app.domains.customer_service.services.notifications import NotificationService


class AssignmentService:
    def __init__(
        self,
        db,
        user_id,
    ):
        self.db = db
        self.repo = TicketAssignmentRepository(db)
        self.user_id = user_id

    async def assign(
        self,
        ticket_id,
        assigned_to,
        meta: dict | None = None,
    ):
        assignment = await self.repo.assign(
            user_id=self.user_id,
            ticket_id=ticket_id,
            assigned_to=assigned_to,
            assigned_by=self.user_id,
            meta=meta,
        )
        if assignment is not None:
            await NotificationService(self.db).create(
                workspace_id=self.user_id,
                recipient_user_id=assigned_to,
                kind="assignment",
                entity_type="ticket",
                entity_id=ticket_id,
                payload={"assigned_by": str(self.user_id)},
            )
        return assignment
