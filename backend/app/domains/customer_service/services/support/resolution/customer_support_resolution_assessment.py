from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.runtime.objectives.resolution import (
    ObjectiveOperationResolution,
    ObjectiveOperationStatus,
    ObjectiveReference,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionContext,
    ObjectiveResolutionSource,
    ObjectiveResolutionStatus,
)


class CustomerSupportResolutionAssessmentAdapter:
    """
    Map customer-support outcome semantics into the
    product-neutral objective-resolution contract.

    This adapter describes remaining work only. It does not
    recommend or authorize repair.
    """

    _OPERATION_STATUS_MAP = {
        "completed": ObjectiveOperationStatus.ACHIEVED,
        "failed": ObjectiveOperationStatus.FAILED,
        "prepared": ObjectiveOperationStatus.PENDING,
        "submitted": ObjectiveOperationStatus.PENDING,
        "rejected": (
            ObjectiveOperationStatus.NOT_EXECUTED
        ),
        "unknown": ObjectiveOperationStatus.UNKNOWN,
    }

    _OBJECTIVE_STATUS_MAP = {
        "achieved": ObjectiveResolutionStatus.ACHIEVED,
        "partially_achieved": (
            ObjectiveResolutionStatus
            .PARTIALLY_ACHIEVED
        ),
        "progressing": (
            ObjectiveResolutionStatus.PROGRESSING
        ),
        "failed": ObjectiveResolutionStatus.FAILED,
        "intentionally_not_executed": (
            ObjectiveResolutionStatus
            .INTENTIONALLY_NOT_EXECUTED
        ),
        "inconclusive": (
            ObjectiveResolutionStatus.INCONCLUSIVE
        ),
    }

    _TERMINAL_RESULTS = {
        "achieved",
        "intentionally_not_executed",
    }

    def assess(
        self,
        context: ObjectiveResolutionContext,
    ) -> ObjectiveResolutionAssessment:
        outcome = context.outcome
        evaluation = context.evaluation

        if outcome is None:
            raise ValueError(
                "customer support outcome is required"
            )

        if evaluation is None:
            raise ValueError(
                "customer support outcome evaluation "
                "is required"
            )

        self._validate_lineage(
            outcome=outcome,
            evaluation=evaluation,
        )

        raw_result = self._string_attr(
            evaluation,
            "result",
        )
        result_value = self._enum_value(
            raw_result
        ).lower()

        try:
            status = self._OBJECTIVE_STATUS_MAP[
                result_value
            ]
        except KeyError as exc:
            raise ValueError(
                "Unsupported customer support evaluation "
                f"result: {result_value or '<blank>'}"
            ) from exc

        operation_payloads = self._operations(
            outcome
        )

        operations = tuple(
            self._operation_resolution(
                outcome=outcome,
                payload=payload,
                sequence=sequence,
            )
            for sequence, payload in enumerate(
                operation_payloads,
                start=1,
            )
        )

        self._validate_evaluation_counters(
            evaluation=evaluation,
            operations=operations,
        )

        evidence_refs = self._evidence_refs(
            evaluation
        )

        objective_namespace = (
            self._string_attr(
                outcome,
                "objective_namespace",
            )
            or "customer_service.support"
        )

        objective_type = (
            self._string_attr(
                outcome,
                "objective_type",
            )
            or "support_resolution"
        )

        objective_ref = (
            self._string_attr(
                outcome,
                "objective_ref",
            )
            or self._string_attr(
                outcome,
                "review_plan_id",
            )
        )

        if not objective_ref:
            raise ValueError(
                "customer support objective ref "
                "is required"
            )

        outcome_ref = self._string_attr(
            outcome,
            "id",
        )
        evaluation_ref = self._string_attr(
            evaluation,
            "id",
        )

        if not outcome_ref:
            raise ValueError(
                "customer support outcome id is required"
            )

        if not evaluation_ref:
            raise ValueError(
                "customer support evaluation id "
                "is required"
            )

        reason_code = self._string_attr(
            evaluation,
            "reason_code",
        )
        summary = self._string_attr(
            evaluation,
            "summary",
        )

        if not reason_code:
            raise ValueError(
                "customer support evaluation reason_code "
                "is required"
            )

        if not summary:
            raise ValueError(
                "customer support evaluation summary "
                "is required"
            )

        confidence = getattr(
            evaluation,
            "confidence",
            None,
        )

        if confidence is None:
            raise ValueError(
                "customer support evaluation confidence "
                "is required"
            )

        source_objective_version = int(
            getattr(
                outcome,
                "source_objective_version",
                1,
            )
            or 1
        )

        outcome_version = int(
            getattr(
                outcome,
                "outcome_version",
                getattr(
                    outcome,
                    "version",
                    1,
                ),
            )
            or 1
        )

        evaluation_version = int(
            getattr(
                evaluation,
                "evaluation_version",
                1,
            )
            or 1
        )

        return ObjectiveResolutionAssessment(
            objective=ObjectiveReference(
                namespace=objective_namespace,
                objective_type=objective_type,
                objective_ref=objective_ref,
                objective_version=(
                    source_objective_version
                ),
            ),
            source=ObjectiveResolutionSource(
                outcome_ref=outcome_ref,
                outcome_version=outcome_version,
                evaluation_ref=evaluation_ref,
                evaluation_version=(
                    evaluation_version
                ),
                workflow_run_id=(
                    self._string_attr(
                        outcome,
                        "workflow_run_id",
                    )
                    or None
                ),
            ),
            status=status,
            reason_code=reason_code,
            summary=summary,
            confidence=float(confidence),
            is_terminal=(
                result_value
                in self._TERMINAL_RESULTS
            ),
            operations=operations,
            evidence_refs=evidence_refs,
            metadata={
                "adapter": (
                    "customer_support_resolution."
                    "v1"
                ),
                "decision": self._string_attr(
                    outcome,
                    "decision",
                ),
                "outcome_status": self._string_attr(
                    outcome,
                    "status",
                ),
            },
        )

    def _operation_resolution(
        self,
        *,
        outcome: Any,
        payload: dict[str, Any],
        sequence: int,
    ) -> ObjectiveOperationResolution:
        operation_type = str(
            payload.get("operation_type")
            or ""
        ).strip().lower()

        if not operation_type:
            raise ValueError(
                "customer support operation_type "
                "is required"
            )

        raw_status = str(
            payload.get("status")
            or "unknown"
        ).strip().lower()

        status = self._OPERATION_STATUS_MAP.get(
            raw_status,
            ObjectiveOperationStatus.UNKNOWN,
        )

        operation_ref = str(
            payload.get("operation_ref")
            or ""
        ).strip()

        if not operation_ref:
            operation_ref = (
                self._legacy_operation_ref(
                    outcome=outcome,
                    payload=payload,
                    sequence=sequence,
                    operation_type=operation_type,
                )
            )

        reason_code = (
            "support_operation_"
            f"{raw_status or 'unknown'}"
        )

        return ObjectiveOperationResolution(
            operation_ref=operation_ref,
            operation_type=operation_type,
            status=status,
            required=True,
            reason_code=reason_code,
            summary=(
                "Customer-support operation "
                f"{operation_type} is {raw_status or 'unknown'}."
            ),
            metadata={
                "legacy_operation_ref": (
                    not bool(
                        str(
                            payload.get(
                                "operation_ref"
                            )
                            or ""
                        ).strip()
                    )
                ),
                "item_id": (
                    str(payload.get("item_id"))
                    if payload.get("item_id")
                    is not None
                    else None
                ),
            },
        )

    @staticmethod
    def _legacy_operation_ref(
        *,
        outcome: Any,
        payload: dict[str, Any],
        sequence: int,
        operation_type: str,
    ) -> str:
        review_plan_id = str(
            getattr(
                outcome,
                "review_plan_id",
                "",
            )
            or ""
        ).strip()

        if not review_plan_id:
            review_plan_id = "unknown_review_plan"

        subject = (
            payload.get("item_id")
            or (
                "address"
                if operation_type
                == "replacement_address"
                else "order"
            )
        )

        def normalize(
            value: Any,
        ) -> str:
            result = "".join(
                character
                if character.isalnum()
                or character in {"-", "_"}
                else "_"
                for character in str(
                    value or ""
                ).strip().lower()
            ).strip("_")

            return result or "unknown"

        return (
            "support_operation:legacy:"
            f"{normalize(review_plan_id)}:"
            f"{sequence:03d}:"
            f"{normalize(operation_type)}:"
            f"{normalize(subject)}"
        )

    @staticmethod
    def _operations(
        outcome: Any,
    ) -> list[dict[str, Any]]:
        raw_operations = getattr(
            outcome,
            "operations_json",
            None,
        )

        if raw_operations is None:
            raw_operations = getattr(
                outcome,
                "operations",
                None,
            )

        result: list[dict[str, Any]] = []

        for item in raw_operations or []:
            if isinstance(item, Mapping):
                result.append(dict(item))
                continue

            model_dump = getattr(
                item,
                "model_dump",
                None,
            )

            if callable(model_dump):
                result.append(
                    dict(
                        model_dump(
                            mode="json",
                        )
                    )
                )
                continue

            raise ValueError(
                "customer support operation payload "
                "must be mapping-compatible"
            )

        return result

    @staticmethod
    def _evidence_refs(
        evaluation: Any,
    ) -> tuple[str, ...]:
        raw_evidence = getattr(
            evaluation,
            "evidence_json",
            None,
        )

        if raw_evidence is None:
            raw_evidence = getattr(
                evaluation,
                "evidence",
                None,
            )

        refs: list[str] = []

        for sequence, item in enumerate(
            raw_evidence or [],
            start=1,
        ):
            if not isinstance(item, Mapping):
                continue

            explicit_ref = str(
                item.get("evidence_ref")
                or item.get("id")
                or ""
            ).strip()

            if explicit_ref:
                refs.append(explicit_ref)
                continue

            source = str(
                item.get("source")
                or "unknown"
            ).strip().lower()
            kind = str(
                item.get("kind")
                or "evidence"
            ).strip().lower()

            refs.append(
                "support_evidence:"
                f"{sequence:03d}:"
                f"{source}:{kind}"
            )

        return tuple(refs)

    @staticmethod
    def _validate_lineage(
        *,
        outcome: Any,
        evaluation: Any,
    ) -> None:
        outcome_id = str(
            getattr(outcome, "id", "")
            or ""
        ).strip()

        evaluation_outcome_id = str(
            getattr(
                evaluation,
                "support_outcome_id",
                "",
            )
            or ""
        ).strip()

        if (
            outcome_id
            and evaluation_outcome_id
            and outcome_id != evaluation_outcome_id
        ):
            raise ValueError(
                "customer support evaluation does not "
                "belong to outcome"
            )

        outcome_review_plan = str(
            getattr(
                outcome,
                "review_plan_id",
                "",
            )
            or ""
        ).strip()

        evaluation_review_plan = str(
            getattr(
                evaluation,
                "review_plan_id",
                "",
            )
            or ""
        ).strip()

        if (
            outcome_review_plan
            and evaluation_review_plan
            and outcome_review_plan
            != evaluation_review_plan
        ):
            raise ValueError(
                "customer support evaluation review plan "
                "does not match outcome"
            )

        outcome_user = str(
            getattr(outcome, "user_id", "")
            or ""
        ).strip()

        evaluation_user = str(
            getattr(evaluation, "user_id", "")
            or ""
        ).strip()

        if (
            outcome_user
            and evaluation_user
            and outcome_user != evaluation_user
        ):
            raise ValueError(
                "customer support evaluation ownership "
                "does not match outcome"
            )

    @staticmethod
    def _validate_evaluation_counters(
        *,
        evaluation: Any,
        operations: tuple[
            ObjectiveOperationResolution,
            ...,
        ],
    ) -> None:
        actual = {
            "achieved_operation_count": sum(
                item.status
                == ObjectiveOperationStatus.ACHIEVED
                for item in operations
            ),
            "failed_operation_count": sum(
                item.status
                == ObjectiveOperationStatus.FAILED
                for item in operations
            ),
            "pending_operation_count": sum(
                item.status
                == ObjectiveOperationStatus.PENDING
                for item in operations
            ),
            "unknown_operation_count": sum(
                item.status
                == ObjectiveOperationStatus.UNKNOWN
                for item in operations
            ),
            "not_executed_operation_count": sum(
                item.status
                == ObjectiveOperationStatus
                .NOT_EXECUTED
                for item in operations
            ),
        }

        for field_name, actual_value in (
            actual.items()
        ):
            expected_value = getattr(
                evaluation,
                field_name,
                None,
            )

            if expected_value is None:
                continue

            if int(expected_value) != actual_value:
                raise ValueError(
                    "customer support evaluation "
                    f"{field_name} does not match "
                    "operation evidence"
                )

    @staticmethod
    def _string_attr(
        value: Any,
        field_name: str,
    ) -> str:
        raw = getattr(
            value,
            field_name,
            "",
        )

        return str(
            raw or ""
        ).strip()

    @staticmethod
    def _enum_value(
        value: Any,
    ) -> str:
        raw_value = getattr(
            value,
            "value",
            value,
        )

        return str(
            raw_value or ""
        ).strip()


__all__ = [
    "CustomerSupportResolutionAssessmentAdapter",
]
