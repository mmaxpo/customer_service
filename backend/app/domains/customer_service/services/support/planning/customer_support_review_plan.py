from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.domains.customer_service.services.support.commerce.commerce_order import (
    CommerceOrder,
)
from app.domains.customer_service.services.support.objective.customer_support_objective import (
    CustomerSupportAction,
    CustomerSupportObjective,
)


class SupportReviewOperationType(StrEnum):
    WHOLE_REFUND = "whole_refund"
    PARTIAL_REFUND = "partial_refund"
    REPLACEMENT = "replacement"
    REPLACEMENT_ADDRESS = "replacement_address"


class SupportReviewOperation(BaseModel):
    operation_ref: str | None = None
    operation_type: SupportReviewOperationType
    item_id: str | None = None
    item_label: str | None = None
    address: dict | None = None
    approval_required: bool = True
    execution_allowed: bool = False


class SupportReviewPlan(BaseModel):
    version: int = 1
    status: str = "awaiting_human_review"
    order_ref: str
    provider: str
    provider_order_id: str | None = None
    operations: list[SupportReviewOperation] = Field(
        default_factory=list
    )
    approval_required: bool = True
    execution_allowed: bool = False
    source_objective_version: int = 1


class CustomerSupportReviewPlanBuilder:
    """
    Convert a completed support objective into a deterministic,
    provider-neutral human-review plan.

    This builder does not invoke providers and never authorizes execution.
    """

    def build(
        self,
        *,
        objective: CustomerSupportObjective,
        order: CommerceOrder,
        source_objective_version: int = 1,
    ) -> SupportReviewPlan:
        if objective.requires_clarification:
            raise ValueError(
                "Cannot build review plan from incomplete objective"
            )

        if objective.mutation_allowed:
            raise ValueError(
                "Completed support objective must remain mutation-blocked"
            )

        item_by_id = {
            (
                item.provider_item_id
                or item.variant_id
                or item.product_id
                or item.title
            ): item
            for item in order.line_items
        }

        operations: list[SupportReviewOperation] = []

        if CustomerSupportAction.WHOLE_REFUND in (
            objective.requested_actions
        ):
            operations.append(
                SupportReviewOperation(
                    operation_type=(
                        SupportReviewOperationType.WHOLE_REFUND
                    ),
                )
            )

        if CustomerSupportAction.PARTIAL_REFUND in (
            objective.requested_actions
        ):
            refund_item_id = objective.item_assignments.get(
                "refund_item"
            )
            refund_item = item_by_id.get(refund_item_id)

            operations.append(
                SupportReviewOperation(
                    operation_type=(
                        SupportReviewOperationType.PARTIAL_REFUND
                    ),
                    item_id=refund_item_id,
                    item_label=(
                        refund_item.title
                        if refund_item is not None
                        else None
                    ),
                )
            )

        if CustomerSupportAction.REPLACEMENT in (
            objective.requested_actions
        ):
            replacement_item_id = (
                objective.item_assignments.get(
                    "replacement_item"
                )
            )
            replacement_item = item_by_id.get(
                replacement_item_id
            )

            operations.append(
                SupportReviewOperation(
                    operation_type=(
                        SupportReviewOperationType.REPLACEMENT
                    ),
                    item_id=replacement_item_id,
                    item_label=(
                        replacement_item.title
                        if replacement_item is not None
                        else None
                    ),
                )
            )

        if CustomerSupportAction.REPLACEMENT_ADDRESS in (
            objective.requested_actions
        ):
            operations.append(
                SupportReviewOperation(
                    operation_type=(
                        SupportReviewOperationType.REPLACEMENT_ADDRESS
                    ),
                    address=objective.replacement_address,
                )
            )

        if not operations:
            raise ValueError(
                "Completed support objective produced no review operations"
            )

        for sequence, operation in enumerate(
            operations,
            start=1,
        ):
            if not operation.operation_ref:
                operation.operation_ref = (
                    self._build_operation_ref(
                        sequence=sequence,
                        operation=operation,
                    )
                )

        return SupportReviewPlan(
            order_ref=order.order_ref,
            provider=order.provider,
            provider_order_id=order.provider_order_id,
            operations=operations,
            source_objective_version=source_objective_version,
        )

    @staticmethod
    def _build_operation_ref(
        *,
        sequence: int,
        operation: SupportReviewOperation,
    ) -> str:
        """
        Build a stable reference unique within this review plan.

        The reference deliberately does not claim global
        uniqueness. Durable consumers pair it with the owning
        objective/review-plan reference.
        """
        subject = (
            operation.item_id
            or (
                "address"
                if operation.operation_type
                == SupportReviewOperationType
                .REPLACEMENT_ADDRESS
                else "order"
            )
        )

        normalized_subject = "".join(
            character
            if character.isalnum()
            or character in {"-", "_"}
            else "_"
            for character in str(subject).strip().lower()
        ).strip("_")

        if not normalized_subject:
            normalized_subject = "subject"

        return (
            "support_operation:"
            f"{sequence:03d}:"
            f"{operation.operation_type.value}:"
            f"{normalized_subject}"
        )
