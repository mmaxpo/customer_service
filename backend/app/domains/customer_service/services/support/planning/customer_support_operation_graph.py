from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperation,
    SupportReviewOperationType,
    SupportReviewPlan,
)


@dataclass(frozen=True)
class CustomerSupportOperationGraph:
    """
    Provider-operation fragment for an already-approved support plan.

    Nodes returned by this object perform provider mutations. The caller
    must connect them only to an approved workflow branch.
    """

    nodes: tuple[dict, ...]
    entry_node_ids: tuple[str, ...]
    result_node_ids: tuple[str, ...]


class CustomerSupportOperationGraphBuilder:
    """
    Build the shared capability-invocation fragment used by both:

    - the original customer-support review workflow;
    - an objective-repair replan workflow.

    This class does not add approval, routing, outcome projection,
    persistence, customer messaging, triggers, joins, or responses.
    """

    def build(
        self,
        *,
        review_plan_id: str,
        review_plan: SupportReviewPlan,
        node_prefix: str = "",
        idempotency_namespace: str = (
            "support-review"
        ),
        use_operation_ref_for_idempotency: bool = True,
        include_operation_metadata: bool = True,
    ) -> CustomerSupportOperationGraph:
        normalized_plan_id = self._required(
            review_plan_id,
            "review_plan_id",
        )
        normalized_prefix = self._normalize_prefix(
            node_prefix
        )
        normalized_namespace = self._required(
            idempotency_namespace,
            "idempotency_namespace",
        )

        self._validate_review_plan(review_plan)

        whole_refund = self._find_operation(
            review_plan,
            SupportReviewOperationType.WHOLE_REFUND,
        )
        partial_refund = self._find_operation(
            review_plan,
            SupportReviewOperationType.PARTIAL_REFUND,
        )
        replacement = self._find_operation(
            review_plan,
            SupportReviewOperationType.REPLACEMENT,
        )
        replacement_address = self._find_operation(
            review_plan,
            SupportReviewOperationType
            .REPLACEMENT_ADDRESS,
        )

        nodes: list[dict] = []
        result_ids: list[str] = []

        if whole_refund is not None:
            node_id = (
                f"{normalized_prefix}"
                "prepare_whole_refund"
            )
            result_ids.append(node_id)

            nodes.append(
                {
                    "id": node_id,
                    "type": "custom",
                    "data": {
                        "nodeType": "capability.invoke",
                        "config": {
                            "capability_id": (
                                "ecommerce.orders.action"
                            ),
                            "payload": {
                                "action": "refund",
                                "order_ref": (
                                    review_plan.order_ref
                                ),
                                "reason": (
                                    "Approved whole-order "
                                    "refund"
                                ),
                                "amount": None,
                                "scope": None,
                                "idempotency_key": (
                                    self._idempotency_key(
                                        namespace=(
                                            normalized_namespace
                                        ),
                                        plan_id=(
                                            normalized_plan_id
                                        ),
                                        operation_ref=(
                                            whole_refund
                                            .operation_ref
                                            if use_operation_ref_for_idempotency
                                            else None
                                        ),
                                        fallback=(
                                            "whole-refund"
                                        ),
                                    )
                                ),
                            },
                            "save_as": (
                                f"{normalized_prefix}"
                                "whole_refund_result"
                            ),
                        },
                        **(
                            {
                                "metadata": (
                                    self._operation_metadata(
                                        whole_refund
                                    )
                                )
                            }
                            if include_operation_metadata
                            else {}
                        ),
                    },
                }
            )

        if partial_refund is not None:
            if not partial_refund.item_id:
                raise ValueError(
                    "Partial-refund operation requires "
                    "item_id"
                )

            node_id = (
                f"{normalized_prefix}"
                "prepare_partial_refund"
            )
            result_ids.append(node_id)

            nodes.append(
                {
                    "id": node_id,
                    "type": "custom",
                    "data": {
                        "nodeType": "capability.invoke",
                        "config": {
                            "capability_id": (
                                "ecommerce.orders.action"
                            ),
                            "payload": {
                                "action": "refund",
                                "order_ref": (
                                    review_plan.order_ref
                                ),
                                "reason": (
                                    "Approved damaged-item "
                                    "partial refund"
                                ),
                                "scope": {
                                    "line_items": [
                                        {
                                            "line_item_id": (
                                                partial_refund
                                                .item_id
                                            ),
                                            "quantity": 1,
                                            "amount": None,
                                        }
                                    ],
                                    (
                                        "replacement_"
                                        "line_item_id"
                                    ): None,
                                    (
                                        "replacement_"
                                        "quantity"
                                    ): None,
                                    "new_address": None,
                                },
                                "idempotency_key": (
                                    self._idempotency_key(
                                        namespace=(
                                            normalized_namespace
                                        ),
                                        plan_id=(
                                            normalized_plan_id
                                        ),
                                        operation_ref=(
                                            partial_refund
                                            .operation_ref
                                            if use_operation_ref_for_idempotency
                                            else None
                                        ),
                                        fallback=(
                                            "partial-refund"
                                        ),
                                    )
                                ),
                            },
                            "save_as": (
                                f"{normalized_prefix}"
                                "partial_refund_result"
                            ),
                        },
                        **(
                            {
                                "metadata": (
                                    self._operation_metadata(
                                        partial_refund
                                    )
                                )
                            }
                            if include_operation_metadata
                            else {}
                        ),
                    },
                }
            )

        if replacement is not None:
            if not replacement.item_id:
                raise ValueError(
                    "Replacement operation requires "
                    "item_id"
                )

            node_id = (
                f"{normalized_prefix}"
                "prepare_replacement"
            )
            result_ids.append(node_id)

            address = (
                deepcopy(
                    replacement_address.address
                )
                if replacement_address is not None
                else None
            )

            nodes.append(
                {
                    "id": node_id,
                    "type": "custom",
                    "data": {
                        "nodeType": "capability.invoke",
                        "config": {
                            "capability_id": (
                                "ecommerce.orders.action"
                            ),
                            "payload": {
                                "action": "reship",
                                "order_ref": (
                                    review_plan.order_ref
                                ),
                                "reason": (
                                    "Approved damaged-item "
                                    "replacement"
                                ),
                                "note": (
                                    "Replacement address "
                                    "approved with support "
                                    "review plan"
                                ),
                                "scope": {
                                    "line_items": [],
                                    (
                                        "replacement_"
                                        "line_item_id"
                                    ): replacement.item_id,
                                    (
                                        "replacement_"
                                        "quantity"
                                    ): 1,
                                    "new_address": address,
                                },
                                "idempotency_key": (
                                    self._idempotency_key(
                                        namespace=(
                                            normalized_namespace
                                        ),
                                        plan_id=(
                                            normalized_plan_id
                                        ),
                                        operation_ref=(
                                            replacement
                                            .operation_ref
                                            if use_operation_ref_for_idempotency
                                            else None
                                        ),
                                        fallback=(
                                            "replacement"
                                        ),
                                    )
                                ),
                            },
                            "save_as": (
                                f"{normalized_prefix}"
                                "replacement_result"
                            ),
                        },
                        **(
                            {
                                "metadata": (
                                    self._operation_metadata(
                                        replacement
                                    )
                                )
                            }
                            if include_operation_metadata
                            else {}
                        ),
                    },
                }
            )

        if not nodes:
            raise ValueError(
                "Review plan contains no executable "
                "provider operation"
            )

        ids = tuple(result_ids)

        return CustomerSupportOperationGraph(
            nodes=tuple(nodes),
            entry_node_ids=ids,
            result_node_ids=ids,
        )

    @staticmethod
    def _validate_review_plan(
        review_plan: SupportReviewPlan,
    ) -> None:
        if not review_plan.order_ref.strip():
            raise ValueError(
                "Support review plan order_ref is required"
            )

        if not review_plan.provider.strip():
            raise ValueError(
                "Support review plan provider is required"
            )

        if not review_plan.approval_required:
            raise ValueError(
                "Support operation graph requires "
                "approval_required=True"
            )

        if review_plan.execution_allowed:
            raise ValueError(
                "Support operation graph requires an "
                "execution-blocked review plan"
            )

    @staticmethod
    def _find_operation(
        review_plan: SupportReviewPlan,
        operation_type: SupportReviewOperationType,
    ) -> SupportReviewOperation | None:
        matches = [
            operation
            for operation in review_plan.operations
            if operation.operation_type
            == operation_type
        ]

        if len(matches) > 1:
            raise ValueError(
                "Support review plan contains more than "
                "one operation of type "
                f"{operation_type.value}"
            )

        return matches[0] if matches else None

    @staticmethod
    def _operation_metadata(
        operation: SupportReviewOperation,
    ) -> dict:
        return {
            "support_operation_ref": (
                operation.operation_ref
            ),
            "support_operation_type": (
                operation.operation_type.value
            ),
            "support_item_id": operation.item_id,
            "support_item_label": (
                operation.item_label
            ),
            "approval_required": True,
            "automatic_execution_allowed": False,
        }

    @classmethod
    def _idempotency_key(
        cls,
        *,
        namespace: str,
        plan_id: str,
        operation_ref: str | None,
        fallback: str,
    ) -> str:
        identity = cls._normalize_identity(
            operation_ref or fallback
        )

        return (
            f"{namespace}:{plan_id}:{identity}"
        )

    @staticmethod
    def _normalize_identity(value: str) -> str:
        normalized = "".join(
            character
            if character.isalnum()
            or character in {"-", "_", ":"}
            else "-"
            for character in str(value).strip()
        ).strip("-")

        return normalized or "operation"

    @staticmethod
    def _normalize_prefix(value: str) -> str:
        normalized = str(value or "").strip()

        if not normalized:
            return ""

        normalized = (
            CustomerSupportOperationGraphBuilder
            ._normalize_identity(normalized)
        )

        return f"{normalized}_"

    @staticmethod
    def _required(
        value: str,
        field_name: str,
    ) -> str:
        normalized = str(value or "").strip()

        if not normalized:
            raise ValueError(
                f"{field_name} is required"
            )

        return normalized


__all__ = [
    "CustomerSupportOperationGraph",
    "CustomerSupportOperationGraphBuilder",
]
