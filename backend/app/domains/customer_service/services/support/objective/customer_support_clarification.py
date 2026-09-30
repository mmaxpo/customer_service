from __future__ import annotations

from pydantic import BaseModel, Field

from app.domains.customer_service.services.support.objective.customer_support_objective import (
    CustomerSupportObjective,
    MissingInformation,
)


class ClarificationQuestion(BaseModel):
    field: MissingInformation
    question: str
    options: list[str] = Field(default_factory=list)


class CustomerSupportClarification(BaseModel):
    required: bool
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    customer_message: str | None = None


class CustomerSupportClarificationService:
    """
    Build customer-facing clarification from a provider-neutral support
    objective and optional commerce order context.

    This service does not execute capabilities or modify provider state.
    """

    def build(
        self,
        *,
        objective: CustomerSupportObjective,
        line_items: list[dict] | None = None,
    ) -> CustomerSupportClarification:
        if not objective.requires_clarification:
            return CustomerSupportClarification(
                required=False,
                questions=[],
                customer_message=None,
            )

        item_options = self._line_item_options(line_items or [])
        questions: list[ClarificationQuestion] = []

        for missing in objective.missing_information:
            if missing == MissingInformation.REFUND_ITEM:
                questions.append(
                    ClarificationQuestion(
                        field=missing,
                        question=(
                            "Which item would you like refunded?"
                        ),
                        options=item_options,
                    )
                )
                continue

            if missing == MissingInformation.REPLACEMENT_ITEM:
                questions.append(
                    ClarificationQuestion(
                        field=missing,
                        question=(
                            "Which item would you like replaced?"
                        ),
                        options=item_options,
                    )
                )
                continue

            if missing == MissingInformation.REPLACEMENT_ADDRESS:
                questions.append(
                    ClarificationQuestion(
                        field=missing,
                        question=(
                            "What address should we use for the replacement?"
                        ),
                    )
                )

        return CustomerSupportClarification(
            required=True,
            questions=questions,
            customer_message=self._customer_message(
                objective=objective,
                questions=questions,
                line_items=line_items or [],
            ),
        )

    def _line_item_options(self, line_items: list[dict]) -> list[str]:
        options: list[str] = []

        for item in line_items:
            title = (
                item.get("title")
                or item.get("name")
                or item.get("product_title")
            )
            variant = item.get("variant_title")
            quantity = item.get("quantity")

            if not title:
                continue

            label = str(title)

            if variant and str(variant).lower() != "default title":
                label = f"{label} — {variant}"

            if quantity not in (None, 1, "1"):
                label = f"{label} (quantity {quantity})"

            options.append(label)

        return options

    def _customer_message(
        self,
        *,
        objective: CustomerSupportObjective,
        questions: list[ClarificationQuestion],
        line_items: list[dict],
    ) -> str:
        parts: list[str] = []

        if objective.order_ref:
            parts.append(
                f"I found order #{objective.order_ref}."
            )

        item_options = self._line_item_options(line_items)

        if item_options:
            rendered_items = "; ".join(
                f"{index}. {option}"
                for index, option in enumerate(item_options, start=1)
            )
            parts.append(
                f"The order contains: {rendered_items}."
            )

        question_text = " ".join(
            question.question
            for question in questions
        )

        if question_text:
            parts.append(question_text)

        parts.append(
            "No refund, replacement, or shipping change will be made "
            "until these details are confirmed."
        )

        return " ".join(parts)
