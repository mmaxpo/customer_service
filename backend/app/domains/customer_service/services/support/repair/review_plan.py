from __future__ import annotations

from copy import deepcopy

from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperation,
    SupportReviewOperationType,
    SupportReviewPlan,
)
from app.runtime.objectives.repair import (
    ObjectiveRepairDisposition,
    ObjectiveRepairPlan,
)


class CustomerSupportRepairReviewPlanBuilder:
    """
    Reconstruct the execution-blocked review-plan subset required
    for one customer-support repair attempt.

    The builder:
    - uses the canonical source SupportReviewPlan;
    - selects only REPLAN_REMAINING targets;
    - preserves original operation references;
    - retains replacement-address scope when replacement is rebuilt;
    - never authorizes provider execution.
    """

    def build(
        self,
        *,
        source_review_plan: SupportReviewPlan,
        repair_plan: ObjectiveRepairPlan,
    ) -> SupportReviewPlan:
        self._validate_source_plan(source_review_plan)

        source_by_ref = self._source_operations_by_ref(
            source_review_plan
        )

        requested_refs = self._replan_target_refs(
            repair_plan
        )

        selected: list[SupportReviewOperation] = []

        for operation_ref in requested_refs:
            source_operation = source_by_ref.get(
                operation_ref
            )

            if source_operation is None:
                raise ValueError(
                    "Repair target operation was not found "
                    "in source review plan: "
                    f"{operation_ref}"
                )

            if (
                source_operation.operation_type
                == SupportReviewOperationType
                .REPLACEMENT_ADDRESS
            ):
                raise ValueError(
                    "Replacement address cannot be replanned "
                    "without its replacement operation"
                )

            selected.append(
                self._blocked_copy(source_operation)
            )

        if not selected:
            raise ValueError(
                "Repair plan contains no "
                "REPLAN_REMAINING operations"
            )

        if self._contains_replacement(selected):
            address_operation = self._find_operation(
                source_review_plan,
                SupportReviewOperationType
                .REPLACEMENT_ADDRESS,
            )

            if address_operation is not None:
                selected.append(
                    self._blocked_copy(
                        address_operation
                    )
                )

        self._validate_selected_operations(selected)

        return SupportReviewPlan(
            version=source_review_plan.version,
            status="awaiting_human_review",
            order_ref=source_review_plan.order_ref,
            provider=source_review_plan.provider,
            provider_order_id=(
                source_review_plan.provider_order_id
            ),
            operations=selected,
            approval_required=True,
            execution_allowed=False,
            source_objective_version=(
                source_review_plan
                .source_objective_version
            ),
        )

    @staticmethod
    def _validate_source_plan(
        source_review_plan: SupportReviewPlan,
    ) -> None:
        if not source_review_plan.order_ref.strip():
            raise ValueError(
                "Source support review plan order_ref "
                "is required"
            )

        if not source_review_plan.provider.strip():
            raise ValueError(
                "Source support review plan provider "
                "is required"
            )

        if not source_review_plan.operations:
            raise ValueError(
                "Source support review plan contains "
                "no operations"
            )

    @staticmethod
    def _source_operations_by_ref(
        source_review_plan: SupportReviewPlan,
    ) -> dict[str, SupportReviewOperation]:
        result: dict[
            str,
            SupportReviewOperation,
        ] = {}

        for operation in source_review_plan.operations:
            operation_ref = str(
                operation.operation_ref or ""
            ).strip()

            if not operation_ref:
                raise ValueError(
                    "Every source review operation must "
                    "have an operation_ref"
                )

            if operation_ref in result:
                raise ValueError(
                    "Source review plan contains duplicate "
                    f"operation_ref: {operation_ref}"
                )

            result[operation_ref] = operation

        return result

    @staticmethod
    def _replan_target_refs(
        repair_plan: ObjectiveRepairPlan,
    ) -> tuple[str, ...]:
        refs: list[str] = []

        for action in repair_plan.actions:
            if (
                action.disposition
                != ObjectiveRepairDisposition
                .REPLAN_REMAINING
            ):
                continue

            for operation_ref in (
                action.target_operation_refs
            ):
                normalized = str(
                    operation_ref or ""
                ).strip()

                if not normalized:
                    raise ValueError(
                        "Repair action contains a blank "
                        "target operation ref"
                    )

                if normalized in refs:
                    raise ValueError(
                        "Repair plan replans the same "
                        "operation more than once: "
                        f"{normalized}"
                    )

                refs.append(normalized)

        return tuple(refs)

    @staticmethod
    def _blocked_copy(
        operation: SupportReviewOperation,
    ) -> SupportReviewOperation:
        copied = operation.model_copy(deep=True)
        copied.approval_required = True
        copied.execution_allowed = False

        if copied.address is not None:
            copied.address = deepcopy(copied.address)

        return copied

    @staticmethod
    def _contains_replacement(
        operations: list[
            SupportReviewOperation
        ],
    ) -> bool:
        return any(
            operation.operation_type
            == SupportReviewOperationType
            .REPLACEMENT
            for operation in operations
        )

    @staticmethod
    def _find_operation(
        review_plan: SupportReviewPlan,
        operation_type: SupportReviewOperationType,
    ) -> SupportReviewOperation | None:
        return next(
            (
                operation
                for operation
                in review_plan.operations
                if operation.operation_type
                == operation_type
            ),
            None,
        )

    @staticmethod
    def _validate_selected_operations(
        operations: list[
            SupportReviewOperation
        ],
    ) -> None:
        executable_types = {
            SupportReviewOperationType.WHOLE_REFUND,
            SupportReviewOperationType.PARTIAL_REFUND,
            SupportReviewOperationType.REPLACEMENT,
        }

        if not any(
            operation.operation_type
            in executable_types
            for operation in operations
        ):
            raise ValueError(
                "Repair review plan contains no "
                "executable preparation operation"
            )

        refs = [
            str(operation.operation_ref or "")
            .strip()
            for operation in operations
        ]

        if any(not ref for ref in refs):
            raise ValueError(
                "Repair review operations must preserve "
                "their original operation refs"
            )

        if len(refs) != len(set(refs)):
            raise ValueError(
                "Repair review plan contains duplicate "
                "operation refs"
            )

        for operation in operations:
            if not operation.approval_required:
                raise ValueError(
                    "Repair review operation must require "
                    "human approval"
                )

            if operation.execution_allowed:
                raise ValueError(
                    "Repair review operation must remain "
                    "execution-blocked"
                )


__all__ = [
    "CustomerSupportRepairReviewPlanBuilder",
]
