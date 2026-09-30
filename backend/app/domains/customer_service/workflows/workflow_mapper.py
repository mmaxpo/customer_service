from app.domains.customer_service.workflows.schemas import (
    SupportIntent,
    WorkflowAction,
)


class CustomerServiceWorkflowMapper:
    def map_intent(self, intent: SupportIntent) -> WorkflowAction:
        if intent == SupportIntent.REFUND:
            return WorkflowAction(
                intent=intent,
                ticket_priority="high",
                requires_human=True,
            )

        if intent == SupportIntent.SHIPPING:
            return WorkflowAction(
                intent=intent,
                ticket_priority="normal",
                requires_human=True,
            )

        if intent == SupportIntent.CANCELLATION:
            return WorkflowAction(
                intent=intent,
                ticket_priority="high",
                requires_human=True,
            )

        if intent == SupportIntent.DAMAGED_PRODUCT:
            return WorkflowAction(
                intent=intent,
                ticket_priority="urgent",
                requires_human=True,
            )

        return WorkflowAction(
            intent=intent,
            ticket_priority="normal",
            requires_human=True,
        )
