from __future__ import annotations

from app.domains.customer_service.services.support.objective.customer_support_objective import (
    CustomerSupportObjectiveInterpreter,
)
from app.domains.customer_service.workflows.message_classifier import (
    CustomerServiceMessageClassifier,
)
from app.domains.customer_service.workflows.schemas import (
    SupportIntent,
)
from app.tcos.planner.operations import (
    OperationType,
    PlanningOperation,
)
from app.tcos.planner.product_planning import (
    PlanCandidate,
    PlannerIntent,
    PlannerIntentName,
    PlanningContext,
    ProductBusinessPlanBuilder,
    ProductPlanningClarification,
    ProductPlanningResult,
)


CUSTOMER_SUPPORT_PRODUCT_ID = "customer_service"

CUSTOMER_SUPPORT_ORDER_STATUS_CAPABILITY = "customer_service.order_status"

CUSTOMER_SUPPORT_ORDER_READ_CAPABILITY = "ecommerce.orders.get"

CUSTOMER_SUPPORT_GENERAL_REPLY_CAPABILITY = (
    "customer_service.customer_reply"
)


class CustomerSupportProductPlanner:
    """
    Product-owned initial planner for Customer Service.

    Customer Service owns interpretation of customer-support language,
    missing-information decisions, and business-plan construction.

    The planner emits semantic capability requirements only. External
    system selection belongs to the Core capability resolver.

    This planner never executes workflows or external operations.
    """

    def __init__(self) -> None:
        self._classifier = CustomerServiceMessageClassifier()
        self._objective_interpreter = CustomerSupportObjectiveInterpreter()

    @property
    def product_id(self) -> str:
        return CUSTOMER_SUPPORT_PRODUCT_ID

    def plan(
        self,
        *,
        intent: PlannerIntent,
        context: PlanningContext | None = None,
    ) -> ProductPlanningResult:
        message = (context.user_message if context is not None else "").strip()

        if not message:
            return self._unclaimed()

        classification = self._classifier.classify(message)

        if classification.intent == SupportIntent.GENERAL:
            if (
                intent.name != PlannerIntentName.CUSTOMER_REPLY
                or not self._is_general_reply_request(message)
            ):
                return self._unclaimed()

            return self._plan_general_reply(
                intent=intent,
                classification=classification,
            )

        if classification.intent != SupportIntent.SHIPPING:
            return self._unclaimed()

        objective = self._objective_interpreter.interpret(message)

        if objective.order_ref is None:
            return ProductPlanningResult(
                product_id=self.product_id,
                claimed=True,
                clarification=(
                    ProductPlanningClarification(
                        reason_code="missing_order_ref",
                        message=(
                            "Please provide your order number so "
                            "I can check the order status. "
                            "No order lookup or modification has "
                            "been performed."
                        ),
                        missing_fields=("order_ref",),
                        metadata={
                            "support_intent": (classification.intent.value),
                            "classification_confidence": (classification.confidence),
                            "planner_intent": str(intent.name),
                        },
                    )
                ),
                metadata={
                    "selected_business_capability": (
                        CUSTOMER_SUPPORT_ORDER_STATUS_CAPABILITY
                    ),
                    "mutation_allowed": False,
                },
            )

        order_ref = f"#{objective.order_ref}"

        operations = self._order_status_operations()

        plan = ProductBusinessPlanBuilder().from_operations(
            plan_id="customer_service_order_status_plan",
            goal_title=CUSTOMER_SUPPORT_ORDER_STATUS_CAPABILITY,
            operations=operations,
            metadata={
                "product_id": self.product_id,
                "support_intent": (classification.intent.value),
                "classification_confidence": (classification.confidence),
                "order_ref": order_ref,
                "selected_business_capability": (
                    CUSTOMER_SUPPORT_ORDER_STATUS_CAPABILITY
                ),
                "semantic_order_capability": (CUSTOMER_SUPPORT_ORDER_READ_CAPABILITY),
                "mutation_allowed": False,
            },
        )

        candidate = PlanCandidate(
            id="generated_customer_service_order_status",
            source="customer_service_product_planner",
            business_plan=plan,
            score=0.0,
            explanation=(
                "Customer Service identified a shipping or "
                "delivery-status request with an order reference."
            ),
            metrics={
                "product_id": self.product_id,
                "support_intent": (classification.intent.value),
                "classification_confidence": (classification.confidence),
                "order_ref": order_ref,
                "selected_capability": (CUSTOMER_SUPPORT_ORDER_STATUS_CAPABILITY),
                "semantic_capabilities": [
                    CUSTOMER_SUPPORT_ORDER_READ_CAPABILITY,
                ],
            },
        )

        return ProductPlanningResult(
            product_id=self.product_id,
            claimed=True,
            candidates=[candidate],
            metadata={
                "selected_business_capability": (
                    CUSTOMER_SUPPORT_ORDER_STATUS_CAPABILITY
                ),
                "mutation_allowed": False,
            },
        )

    @staticmethod
    def _is_general_reply_request(message: str) -> bool:
        normalized = message.strip().lower()

        reply_signals = (
            "reply",
            "answer",
            "respond",
            "tell the customer",
            "customer says",
            "customer said",
            "customer wrote",
            "customer message",
            "customer asked",
        )

        return any(
            signal in normalized
            for signal in reply_signals
        )

    def _plan_general_reply(
        self,
        *,
        intent: PlannerIntent,
        classification,
    ) -> ProductPlanningResult:
        operations = [
            PlanningOperation(
                id="search_knowledge",
                capability_id="agent_tool.knowledge_search",
                operation_type=OperationType.ACQUIRE_INFORMATION,
                purpose="Search Customer Service knowledge.",
                outputs=["knowledge_context"],
            ),
            PlanningOperation(
                id="generate_reply",
                capability_id="runtime.agent_custom",
                operation_type=OperationType.ANALYZE,
                purpose="Generate a customer reply using support knowledge.",
                inputs=["knowledge_context"],
                outputs=["customer_reply"],
                depends_on=["search_knowledge"],
            ),
            PlanningOperation(
                id="send_response",
                capability_id="runtime.response",
                operation_type=OperationType.COMMUNICATE,
                purpose="Return the customer reply.",
                inputs=["customer_reply"],
                depends_on=["generate_reply"],
            ),
        ]

        plan = ProductBusinessPlanBuilder().from_operations(
            plan_id="customer_service_general_reply_plan",
            goal_title=CUSTOMER_SUPPORT_GENERAL_REPLY_CAPABILITY,
            operations=operations,
            metadata={
                "product_id": self.product_id,
                "support_intent": classification.intent.value,
                "classification_confidence": classification.confidence,
                "planner_intent": str(intent.name),
                "selected_business_capability": (
                    CUSTOMER_SUPPORT_GENERAL_REPLY_CAPABILITY
                ),
                "mutation_allowed": False,
            },
        )

        candidate = PlanCandidate(
            id="generated_customer_service_customer_reply",
            source="customer_service_product_planner",
            business_plan=plan,
            score=0.0,
            explanation=(
                "Customer Service identified a general customer-reply "
                "request."
            ),
            metrics={
                "product_id": self.product_id,
                "support_intent": classification.intent.value,
                "classification_confidence": classification.confidence,
                "selected_capability": (
                    CUSTOMER_SUPPORT_GENERAL_REPLY_CAPABILITY
                ),
            },
        )

        return ProductPlanningResult(
            product_id=self.product_id,
            claimed=True,
            candidates=[candidate],
            metadata={
                "selected_business_capability": (
                    CUSTOMER_SUPPORT_GENERAL_REPLY_CAPABILITY
                ),
                "mutation_allowed": False,
            },
        )

    def _unclaimed(self) -> ProductPlanningResult:
        return ProductPlanningResult(
            product_id=self.product_id,
            claimed=False,
        )

    @staticmethod
    def _order_status_operations() -> list[PlanningOperation]:
        return [
            PlanningOperation(
                id="extract_order_reference",
                capability_id=("customer_service.extract_order_ref"),
                operation_type=(OperationType.ACQUIRE_INFORMATION),
                purpose=("Extract order reference from customer message."),
                outputs=["order_ref"],
            ),
            PlanningOperation(
                id="lookup_order",
                capability_id=(CUSTOMER_SUPPORT_ORDER_READ_CAPABILITY),
                operation_type=(OperationType.ACQUIRE_INFORMATION),
                purpose="Retrieve commerce order.",
                inputs=["order_ref"],
                outputs=["commerce_order"],
                depends_on=[
                    "extract_order_reference",
                ],
            ),
            PlanningOperation(
                id="prepare_customer_answer",
                capability_id="runtime.agent_custom",
                operation_type=OperationType.ANALYZE,
                purpose=("Prepare response using order information."),
                inputs=["commerce_order"],
                outputs=["customer_reply"],
                depends_on=["lookup_order"],
            ),
            PlanningOperation(
                id="send_customer_reply",
                capability_id="runtime.response",
                operation_type=OperationType.COMMUNICATE,
                purpose="Return response to customer.",
                inputs=["customer_reply"],
                depends_on=[
                    "prepare_customer_answer",
                ],
            ),
        ]


__all__ = [
    "CUSTOMER_SUPPORT_GENERAL_REPLY_CAPABILITY",
    "CUSTOMER_SUPPORT_ORDER_READ_CAPABILITY",
    "CUSTOMER_SUPPORT_ORDER_STATUS_CAPABILITY",
    "CUSTOMER_SUPPORT_PRODUCT_ID",
    "CustomerSupportProductPlanner",
]
