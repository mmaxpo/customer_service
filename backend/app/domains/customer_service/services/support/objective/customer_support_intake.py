from __future__ import annotations

from pydantic import BaseModel

from app.domains.customer_service.services.support.commerce.commerce_order import (
    CommerceOrder,
)
from app.domains.customer_service.services.support.objective.customer_support_clarification import (
    CustomerSupportClarification,
    CustomerSupportClarificationService,
)
from app.domains.customer_service.services.support.objective.customer_support_objective import (
    CustomerSupportObjective,
    CustomerSupportObjectiveInterpreter,
)


class CustomerSupportIntakeResult(BaseModel):
    objective: CustomerSupportObjective
    clarification: CustomerSupportClarification
    mutation_allowed: bool = False


class CustomerSupportIntakeService:
    """
    Provider-neutral customer-service intake.

    It interprets a customer objective and builds clarification from a
    normalized commerce order. It never performs provider mutations.
    """

    def assess(
        self,
        *,
        message: str,
        order: CommerceOrder | None = None,
    ) -> CustomerSupportIntakeResult:
        objective = CustomerSupportObjectiveInterpreter().interpret(
            message
        )

        line_items = []

        if order is not None:
            line_items = [
                item.model_dump(mode="json")
                for item in order.line_items
            ]

        clarification = CustomerSupportClarificationService().build(
            objective=objective,
            line_items=line_items,
        )

        return CustomerSupportIntakeResult(
            objective=objective,
            clarification=clarification,
            mutation_allowed=False,
        )
