from __future__ import annotations

from app.runtime.objectives.repair import (
    ObjectiveRepairAction,
    ObjectiveRepairDisposition,
    ObjectiveRepairPlan,
    ObjectiveRepairPlanningContext,
    ObjectiveRepairTarget,
)
from app.runtime.objectives.resolution import (
    ObjectiveOperationStatus,
)


CUSTOMER_SUPPORT_REPAIR_POLICY_VERSION = 1

CUSTOMER_SUPPORT_OPERATION_STATUS_CHANGED_EVENT = (
    "customer_service.support.operation.status_changed"
)

CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE = (
    "customer_service.support"
)

CUSTOMER_SUPPORT_OBJECTIVE_TYPES = {
    "support_resolution",
    "multi_operation",
}

SUPPORTED_CUSTOMER_SUPPORT_OPERATION_TYPES = {
    "whole_refund",
    "partial_refund",
    "replacement",
    "replacement_address",
}


class CustomerSupportObjectiveRepairPlanner:
    """
    Product-owned continuation policy for unresolved customer
    support objectives.

    Safety policy:
    - provider mutations are never automatically authorized;
    - failed operations are replanned behind new approval;
    - pending operations wait rather than duplicate work;
    - unknown or unsupported operations require human review.
    """

    def plan_repair(
        self,
        context: ObjectiveRepairPlanningContext,
    ) -> ObjectiveRepairPlan:
        request = context.request
        resolution = context.resolution

        self._validate_context(context)

        actions = tuple(
            self._action_for_target(
                request=request,
                target=target,
                sequence=sequence,
            )
            for sequence, target in enumerate(
                request.targets,
                start=1,
            )
        )

        disposition = self._controlling_disposition(
            tuple(
                action.disposition
                for action in actions
            )
        )

        human_approval_required = (
            request.constraints.require_human_approval
            or any(
                action.human_approval_required
                for action in actions
            )
        )

        return ObjectiveRepairPlan(
            repair_request_ref=(
                request.repair_request_ref
            ),
            objective=request.source.objective,
            disposition=disposition,
            reason_code=(
                self._plan_reason_code(disposition)
            ),
            summary=self._plan_summary(
                disposition=disposition,
                target_count=len(request.targets),
            ),
            confidence=min(
                request.resolution_confidence,
                min(
                    action.confidence
                    for action in actions
                ),
            ),
            actions=actions,
            planned_target_refs=tuple(
                target.operation_ref
                for target in request.targets
            ),
            deferred_target_refs=(),
            unhandled_target_refs=(),
            automatic_execution_allowed=False,
            human_approval_required=(
                human_approval_required
            ),
            planner_metadata={
                "planner": (
                    "customer_support_objective_repair.v1"
                ),
                "policy_version": (
                    CUSTOMER_SUPPORT_REPAIR_POLICY_VERSION
                ),
                "automatic_mutation_allowed": False,
                "target_count": len(
                    request.targets
                ),
                "source_resolution_record_ref": (
                    request.source
                    .resolution_record_ref
                ),
                "source_status": (
                    resolution.status.value
                ),
            },
        )

    def _validate_context(
        self,
        context: ObjectiveRepairPlanningContext,
    ) -> None:
        request = context.request
        resolution = context.resolution

        objective = request.source.objective

        if (
            objective.namespace
            != CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE
        ):
            raise ValueError(
                "customer support repair request has "
                "unsupported objective namespace"
            )

        if (
            objective.objective_type
            not in CUSTOMER_SUPPORT_OBJECTIVE_TYPES
        ):
            raise ValueError(
                "customer support repair request has "
                "unsupported objective type"
            )

        if objective != resolution.objective:
            raise ValueError(
                "customer support repair request objective "
                "does not match resolution"
            )

        if (
            request.source.outcome_ref
            != resolution.source.outcome_ref
            or request.source.outcome_version
            != resolution.source.outcome_version
        ):
            raise ValueError(
                "customer support repair request outcome "
                "lineage does not match resolution"
            )

        if (
            request.source.evaluation_ref
            != resolution.source.evaluation_ref
            or request.source.evaluation_version
            != resolution.source.evaluation_version
        ):
            raise ValueError(
                "customer support repair request evaluation "
                "lineage does not match resolution"
            )

        request_target_refs = tuple(
            target.operation_ref
            for target in request.targets
        )

        if (
            request_target_refs
            != resolution.unresolved_operation_refs
        ):
            raise ValueError(
                "customer support repair request targets "
                "do not match unresolved resolution "
                "operations"
            )

        resolution_by_ref = {
            operation.operation_ref: operation
            for operation in resolution.operations
        }

        for target in request.targets:
            operation = resolution_by_ref.get(
                target.operation_ref
            )

            if operation is None:
                raise ValueError(
                    "customer support repair target is not "
                    "present in resolution"
                )

            if (
                target.operation_type
                != operation.operation_type
                or target.resolution_status
                != operation.status
                or target.required
                != operation.required
            ):
                raise ValueError(
                    "customer support repair target facts "
                    "do not match resolution"
                )

    def _action_for_target(
        self,
        *,
        request,
        target: ObjectiveRepairTarget,
        sequence: int,
    ) -> ObjectiveRepairAction:
        desired = self._desired_disposition(target)

        disposition = self._safe_allowed_disposition(
            desired=desired,
            allowed=(
                request.constraints
                .allowed_dispositions
            ),
        )

        action_ref = self._action_ref(
            repair_request_ref=(
                request.repair_request_ref
            ),
            sequence=sequence,
            disposition=disposition,
            operation_ref=target.operation_ref,
        )

        if (
            disposition
            == ObjectiveRepairDisposition
            .WAIT_FOR_RESULT
        ):
            return ObjectiveRepairAction(
                action_ref=action_ref,
                disposition=disposition,
                target_operation_refs=(
                    target.operation_ref,
                ),
                reason_code=(
                    "support_operation_pending"
                ),
                summary=(
                    "Wait for the existing support "
                    "operation to report a conclusive "
                    "result before further mutation."
                ),
                confidence=0.95,
                automatic_execution_allowed=False,
                human_approval_required=False,
                wait_for_event_type=(
                    CUSTOMER_SUPPORT_OPERATION_STATUS_CHANGED_EVENT
                ),
                planner_directives={
                    "preserve_original_operation": True,
                    "do_not_duplicate_mutation": True,
                    "reverify_after_signal": True,
                },
                metadata=self._safe_target_metadata(
                    target
                ),
            )

        if (
            disposition
            == ObjectiveRepairDisposition
            .REPLAN_REMAINING
        ):
            return ObjectiveRepairAction(
                action_ref=action_ref,
                disposition=disposition,
                target_operation_refs=(
                    target.operation_ref,
                ),
                reason_code=(
                    "support_operation_failed_requires_replan"
                ),
                summary=(
                    "Rebuild only the failed support "
                    "operation and require a new human "
                    "approval before provider execution."
                ),
                confidence=0.9,
                automatic_execution_allowed=False,
                human_approval_required=True,
                planner_directives={
                    "preserve_achieved_operations": True,
                    "rebuild_only_target_operations": True,
                    "require_new_human_approval": True,
                    "reuse_original_operation_ref": True,
                },
                metadata=self._safe_target_metadata(
                    target
                ),
            )

        if (
            disposition
            == ObjectiveRepairDisposition
            .REQUEST_HUMAN_ACTION
        ):
            unsupported = (
                target.operation_type
                not in (
                    SUPPORTED_CUSTOMER_SUPPORT_OPERATION_TYPES
                )
            )

            return ObjectiveRepairAction(
                action_ref=action_ref,
                disposition=disposition,
                target_operation_refs=(
                    target.operation_ref,
                ),
                reason_code=(
                    "unsupported_support_operation_type"
                    if unsupported
                    else (
                        "support_operation_requires_"
                        "human_verification"
                    )
                ),
                summary=(
                    "A human must verify the external "
                    "operation state before any additional "
                    "provider mutation."
                    if not unsupported
                    else (
                        "The support operation type is not "
                        "supported by the current repair "
                        "policy and requires human review."
                    )
                ),
                confidence=0.85,
                automatic_execution_allowed=False,
                human_approval_required=True,
                planner_directives={
                    "verify_external_state": True,
                    "do_not_execute_provider_mutation": True,
                    "capture_resolution_evidence": True,
                },
                metadata=self._safe_target_metadata(
                    target
                ),
            )

        if (
            disposition
            == ObjectiveRepairDisposition.STOP_REPAIR
        ):
            return ObjectiveRepairAction(
                action_ref=action_ref,
                disposition=disposition,
                target_operation_refs=(
                    target.operation_ref,
                ),
                reason_code=(
                    "no_safe_support_repair_disposition"
                ),
                summary=(
                    "No safe allowed continuation is "
                    "available for this support operation."
                ),
                confidence=1.0,
                automatic_execution_allowed=False,
                human_approval_required=False,
                planner_directives={
                    "do_not_continue_automatically": True,
                },
                metadata=self._safe_target_metadata(
                    target
                ),
            )

        raise ValueError(
            "customer support repair planner selected an "
            "unsupported disposition"
        )

    @staticmethod
    def _desired_disposition(
        target: ObjectiveRepairTarget,
    ) -> ObjectiveRepairDisposition:
        if (
            target.operation_type
            not in SUPPORTED_CUSTOMER_SUPPORT_OPERATION_TYPES
        ):
            return (
                ObjectiveRepairDisposition
                .REQUEST_HUMAN_ACTION
            )

        if (
            target.resolution_status
            == ObjectiveOperationStatus.PENDING
        ):
            return (
                ObjectiveRepairDisposition
                .WAIT_FOR_RESULT
            )

        if (
            target.resolution_status
            == ObjectiveOperationStatus.FAILED
        ):
            return (
                ObjectiveRepairDisposition
                .REPLAN_REMAINING
            )

        if (
            target.resolution_status
            == ObjectiveOperationStatus.UNKNOWN
        ):
            return (
                ObjectiveRepairDisposition
                .REQUEST_HUMAN_ACTION
            )

        raise ValueError(
            "customer support repair target has "
            "unsupported resolution status"
        )

    @staticmethod
    def _safe_allowed_disposition(
        *,
        desired: ObjectiveRepairDisposition,
        allowed: tuple[
            ObjectiveRepairDisposition,
            ...,
        ],
    ) -> ObjectiveRepairDisposition:
        allowed_set = set(allowed)

        if desired in allowed_set:
            return desired

        if (
            ObjectiveRepairDisposition
            .REQUEST_HUMAN_ACTION
            in allowed_set
        ):
            return (
                ObjectiveRepairDisposition
                .REQUEST_HUMAN_ACTION
            )

        if (
            ObjectiveRepairDisposition.STOP_REPAIR
            in allowed_set
        ):
            return (
                ObjectiveRepairDisposition.STOP_REPAIR
            )

        raise ValueError(
            "customer support repair request does not "
            "allow a safe disposition"
        )

    @staticmethod
    def _controlling_disposition(
        dispositions: tuple[
            ObjectiveRepairDisposition,
            ...,
        ],
    ) -> ObjectiveRepairDisposition:
        present = set(dispositions)

        precedence = (
            ObjectiveRepairDisposition
            .REQUEST_HUMAN_ACTION,
            ObjectiveRepairDisposition
            .REPLAN_REMAINING,
            ObjectiveRepairDisposition
            .WAIT_FOR_RESULT,
            ObjectiveRepairDisposition
            .RETRY_OPERATION,
            ObjectiveRepairDisposition.STOP_REPAIR,
        )

        for disposition in precedence:
            if disposition in present:
                return disposition

        raise ValueError(
            "customer support repair plan has no "
            "controlling disposition"
        )

    @staticmethod
    def _action_ref(
        *,
        repair_request_ref: str,
        sequence: int,
        disposition: ObjectiveRepairDisposition,
        operation_ref: str,
    ) -> str:
        def normalize(value: str) -> str:
            normalized = "".join(
                character
                if character.isalnum()
                or character in {"-", "_", ":"}
                else "_"
                for character in str(value).strip().lower()
            ).strip("_")

            return normalized or "unknown"

        return (
            "support-repair:"
            f"{normalize(repair_request_ref)}:"
            f"{sequence:03d}:"
            f"{disposition.value}:"
            f"{normalize(operation_ref)}"
        )

    @staticmethod
    def _safe_target_metadata(
        target: ObjectiveRepairTarget,
    ) -> dict[str, object]:
        return {
            "operation_ref": target.operation_ref,
            "operation_type": target.operation_type,
            "resolution_status": (
                target.resolution_status.value
            ),
            "source_reason_code": (
                target.reason_code
            ),
            "source_task_id": (
                target.source_task_id
            ),
            "verification_ref": (
                target.verification_ref
            ),
        }

    @staticmethod
    def _plan_reason_code(
        disposition: ObjectiveRepairDisposition,
    ) -> str:
        return {
            ObjectiveRepairDisposition
            .REQUEST_HUMAN_ACTION: (
                "support_repair_requires_human_action"
            ),
            ObjectiveRepairDisposition
            .REPLAN_REMAINING: (
                "support_repair_requires_replanning"
            ),
            ObjectiveRepairDisposition
            .WAIT_FOR_RESULT: (
                "support_repair_waiting_for_result"
            ),
            ObjectiveRepairDisposition
            .RETRY_OPERATION: (
                "support_repair_retry"
            ),
            ObjectiveRepairDisposition.STOP_REPAIR: (
                "support_repair_stopped"
            ),
        }[disposition]

    @staticmethod
    def _plan_summary(
        *,
        disposition: ObjectiveRepairDisposition,
        target_count: int,
    ) -> str:
        return (
            "Customer-support repair policy planned "
            f"{target_count} unresolved operation"
            f"{'' if target_count == 1 else 's'} with "
            f"controlling disposition "
            f"{disposition.value}."
        )


__all__ = [
    "CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE",
    "CUSTOMER_SUPPORT_OBJECTIVE_TYPES",
    "CUSTOMER_SUPPORT_OPERATION_STATUS_CHANGED_EVENT",
    "CUSTOMER_SUPPORT_REPAIR_POLICY_VERSION",
    "SUPPORTED_CUSTOMER_SUPPORT_OPERATION_TYPES",
    "CustomerSupportObjectiveRepairPlanner",
]
