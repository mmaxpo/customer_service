from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperation,
    SupportReviewOperationType,
    SupportReviewPlan,
)


class SupportOutcomeStatus(StrEnum):
    REJECTED = "rejected"
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


class SupportOperationOutcome(BaseModel):
    operation_ref: str | None = None
    operation_type: SupportReviewOperationType
    status: SupportOutcomeStatus

    item_id: str | None = None
    item_label: str | None = None

    prepared: bool = False
    submitted: bool = False
    completed: bool = False

    provider_result: dict[str, Any] = Field(default_factory=dict)


class CustomerSupportOutcome(BaseModel):
    version: int = 1

    review_plan_id: str
    order_ref: str

    decision: Literal["approved", "rejected"]

    operations: list[SupportOperationOutcome] = Field(
        default_factory=list
    )

    customer_message: str


class CustomerSupportOutcomeProjector:
    """
    Project durable support-review execution state into a provider-neutral
    customer-service outcome.

    This service owns customer-support semantics.

    It deliberately does not:
    - call Shopify or any provider,
    - write chat messages,
    - assume capability success means business completion,
    - expose raw provider wording to the customer.
    """

    _RESULT_KEY_BY_OPERATION = {
        SupportReviewOperationType.WHOLE_REFUND: (
            "prepare_whole_refund"
        ),
        SupportReviewOperationType.PARTIAL_REFUND: (
            "prepare_partial_refund"
        ),
        SupportReviewOperationType.REPLACEMENT: (
            "prepare_replacement"
        ),
    }

    def project(
        self,
        *,
        review_plan_id: str,
        support_review: dict[str, Any],
        approval_result: bool,
        prepared_operations: dict[str, Any] | None = None,
    ) -> CustomerSupportOutcome:
        normalized_plan_id = str(review_plan_id or "").strip()
        if not normalized_plan_id:
            raise ValueError("review_plan_id is required")

        review_plan_payload = support_review.get("review_plan")
        if not isinstance(review_plan_payload, dict):
            raise ValueError(
                "support_review.review_plan is required"
            )

        review_plan = SupportReviewPlan.model_validate(
            review_plan_payload
        )

        if not approval_result:
            return self._project_rejected(
                review_plan_id=normalized_plan_id,
                review_plan=review_plan,
            )

        return self._project_approved(
            review_plan_id=normalized_plan_id,
            review_plan=review_plan,
            prepared_operations=prepared_operations or {},
        )

    def _project_rejected(
        self,
        *,
        review_plan_id: str,
        review_plan: SupportReviewPlan,
    ) -> CustomerSupportOutcome:
        executable_operations = self._executable_operations(
            review_plan
        )

        operation_outcomes = [
            SupportOperationOutcome(
                operation_ref=operation.operation_ref,
                operation_type=operation.operation_type,
                status=SupportOutcomeStatus.REJECTED,
                item_id=operation.item_id,
                item_label=operation.item_label,
            )
            for operation in executable_operations
        ]

        return CustomerSupportOutcome(
            review_plan_id=review_plan_id,
            order_ref=review_plan.order_ref,
            decision="rejected",
            operations=operation_outcomes,
            customer_message=self._rejected_message(
                review_plan=review_plan,
                operations=executable_operations,
            ),
        )

    def _project_approved(
        self,
        *,
        review_plan_id: str,
        review_plan: SupportReviewPlan,
        prepared_operations: dict[str, Any],
    ) -> CustomerSupportOutcome:
        executable_operations = self._executable_operations(
            review_plan
        )

        outcomes: list[SupportOperationOutcome] = []

        for operation in executable_operations:
            result_key = self._RESULT_KEY_BY_OPERATION[
                operation.operation_type
            ]

            raw_result = prepared_operations.get(result_key)

            result = (
                raw_result
                if isinstance(raw_result, dict)
                else {}
            )

            status = self._normalize_status(result)

            outcomes.append(
                SupportOperationOutcome(
                    operation_ref=operation.operation_ref,
                    operation_type=operation.operation_type,
                    status=status,
                    item_id=operation.item_id,
                    item_label=operation.item_label,
                    prepared=(
                        status
                        in {
                            SupportOutcomeStatus.PREPARED,
                            SupportOutcomeStatus.SUBMITTED,
                            SupportOutcomeStatus.COMPLETED,
                        }
                    ),
                    submitted=(
                        status
                        in {
                            SupportOutcomeStatus.SUBMITTED,
                            SupportOutcomeStatus.COMPLETED,
                        }
                    ),
                    completed=(
                        status
                        == SupportOutcomeStatus.COMPLETED
                    ),
                    provider_result=result,
                )
            )

        return CustomerSupportOutcome(
            review_plan_id=review_plan_id,
            order_ref=review_plan.order_ref,
            decision="approved",
            operations=outcomes,
            customer_message=self._approved_message(
                review_plan=review_plan,
                outcomes=outcomes,
            ),
        )

    @staticmethod
    def _executable_operations(
        review_plan: SupportReviewPlan,
    ) -> list[SupportReviewOperation]:
        return [
            operation
            for operation in review_plan.operations
            if operation.operation_type
            != SupportReviewOperationType.REPLACEMENT_ADDRESS
        ]

    @staticmethod
    def _normalize_status(
        result: dict[str, Any],
    ) -> SupportOutcomeStatus:
        status = str(result.get("status") or "").strip().lower()

        if status == "prepared":
            return SupportOutcomeStatus.PREPARED

        if status in {"submitted", "processing"}:
            return SupportOutcomeStatus.SUBMITTED

        if status in {
            "completed",
            "complete",
            "refunded",
            "fulfilled",
        }:
            return SupportOutcomeStatus.COMPLETED

        if status in {
            "failed",
            "error",
            "rejected",
            "cancelled",
            "canceled",
        }:
            return SupportOutcomeStatus.FAILED

        return SupportOutcomeStatus.UNKNOWN

    @staticmethod
    def _has_refund(
        operation_types: set[SupportReviewOperationType],
    ) -> bool:
        return bool(
            operation_types
            & {
                SupportReviewOperationType.WHOLE_REFUND,
                SupportReviewOperationType.PARTIAL_REFUND,
            }
        )

    @staticmethod
    def _has_replacement(
        operation_types: set[SupportReviewOperationType],
    ) -> bool:
        return (
            SupportReviewOperationType.REPLACEMENT
            in operation_types
        )

    def _rejected_message(
        self,
        *,
        review_plan: SupportReviewPlan,
        operations: list[SupportReviewOperation],
    ) -> str:
        operation_types = {
            operation.operation_type
            for operation in operations
        }

        has_refund = self._has_refund(operation_types)
        has_replacement = self._has_replacement(
            operation_types
        )

        if has_refund and not has_replacement:
            return (
                f"Your refund request for order "
                f"{review_plan.order_ref} was not approved. "
                "No refund was submitted."
            )

        if has_replacement and not has_refund:
            return (
                f"Your replacement request for order "
                f"{review_plan.order_ref} was not approved. "
                "No replacement was submitted."
            )

        return (
            f"Your support request for order "
            f"{review_plan.order_ref} was not approved. "
            "No order action was submitted."
        )

    def _approved_message(
        self,
        *,
        review_plan: SupportReviewPlan,
        outcomes: list[SupportOperationOutcome],
    ) -> str:
        operation_types = {
            outcome.operation_type
            for outcome in outcomes
        }

        statuses = {
            outcome.status
            for outcome in outcomes
        }

        has_refund = self._has_refund(operation_types)
        has_replacement = self._has_replacement(
            operation_types
        )

        if len(outcomes) == 1 and has_refund:
            return self._single_refund_message(
                order_ref=review_plan.order_ref,
                status=outcomes[0].status,
            )

        if len(outcomes) == 1 and has_replacement:
            return self._single_replacement_message(
                order_ref=review_plan.order_ref,
                status=outcomes[0].status,
            )

        if statuses == {SupportOutcomeStatus.PREPARED}:
            return (
                f"Your support request for order "
                f"{review_plan.order_ref} was approved. "
                "The requested actions have been prepared, "
                "but they have not been submitted yet."
            )

        if statuses <= {
            SupportOutcomeStatus.SUBMITTED,
            SupportOutcomeStatus.COMPLETED,
        }:
            return (
                f"Your support request for order "
                f"{review_plan.order_ref} was approved and "
                "the requested actions have been submitted "
                "for processing."
            )

        if SupportOutcomeStatus.FAILED in statuses:
            return (
                f"Your support request for order "
                f"{review_plan.order_ref} was approved, but "
                "we could not complete all requested actions. "
                "A support agent can review it."
            )

        return (
            f"Your support request for order "
            f"{review_plan.order_ref} was approved. "
            "A support agent can confirm the latest processing "
            "status."
        )

    @staticmethod
    def _single_refund_message(
        *,
        order_ref: str,
        status: SupportOutcomeStatus,
    ) -> str:
        if status == SupportOutcomeStatus.PREPARED:
            return (
                f"Your refund request for order "
                f"{order_ref} was approved. "
                "The refund has been prepared, but it has "
                "not been submitted yet."
            )

        if status == SupportOutcomeStatus.SUBMITTED:
            return (
                f"Your refund request for order "
                f"{order_ref} was approved and the refund "
                "has been submitted for processing."
            )

        if status == SupportOutcomeStatus.COMPLETED:
            return (
                f"Your refund for order {order_ref} "
                "has been completed."
            )

        if status == SupportOutcomeStatus.FAILED:
            return (
                f"Your refund request for order "
                f"{order_ref} was approved, but we could not "
                "complete the refund. A support agent can "
                "review it."
            )

        return (
            f"Your refund request for order {order_ref} "
            "was approved. A support agent can confirm the "
            "latest refund status."
        )

    @staticmethod
    def _single_replacement_message(
        *,
        order_ref: str,
        status: SupportOutcomeStatus,
    ) -> str:
        if status == SupportOutcomeStatus.PREPARED:
            return (
                f"Your replacement request for order "
                f"{order_ref} was approved. "
                "The replacement has been prepared, but it "
                "has not been submitted yet."
            )

        if status == SupportOutcomeStatus.SUBMITTED:
            return (
                f"Your replacement request for order "
                f"{order_ref} was approved and has been "
                "submitted for processing."
            )

        if status == SupportOutcomeStatus.COMPLETED:
            return (
                f"Your replacement request for order "
                f"{order_ref} has been completed."
            )

        if status == SupportOutcomeStatus.FAILED:
            return (
                f"Your replacement request for order "
                f"{order_ref} was approved, but we could not "
                "complete the replacement. A support agent "
                "can review it."
            )

        return (
            f"Your replacement request for order "
            f"{order_ref} was approved. A support agent can "
            "confirm the latest replacement status."
        )
