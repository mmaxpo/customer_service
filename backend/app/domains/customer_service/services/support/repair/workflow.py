from __future__ import annotations

from app.domains.customer_service.services.support.planning.customer_support_operation_graph import (
    CustomerSupportOperationGraphBuilder,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewPlan,
)
from app.runtime.objectives.repair import (
    ObjectiveRepairAction,
    ObjectiveRepairDisposition,
    ObjectiveRepairPlan,
)


class CustomerSupportRepairWorkflowBuilder:
    """
    Build durable non-mutating customer-support repair-control
    workflows.

    Supported in this slice:
    - WAIT_FOR_RESULT
    - REQUEST_HUMAN_ACTION
    - STOP_REPAIR

    REPLAN_REMAINING is deliberately handled by the separate
    provider-operation workflow integration because it must reuse
    the existing approval and capability-invocation implementation.
    """

    def build_replanned_operations(
        self,
        *,
        repair_execution_id: str,
        resolution_record_id: str,
        attempt_number: int,
        repair_plan: ObjectiveRepairPlan,
        repair_review_plan: SupportReviewPlan,
    ) -> dict:
        """
        Build an approval-first workflow for provider operations
        reconstructed by CustomerSupportRepairReviewPlanBuilder.

        This workflow deliberately does not:
        - record a canonical customer-support outcome;
        - send a customer chat message;
        - update durable repair execution status.

        Those lifecycle responsibilities belong to the repair
        coordinator introduced in the subsequent wiring slice.
        """

        execution_id = self._required(
            repair_execution_id,
            "repair_execution_id",
        )
        resolution_id = self._required(
            resolution_record_id,
            "resolution_record_id",
        )

        if attempt_number < 1:
            raise ValueError(
                "attempt_number must be >= 1"
            )

        self._validate_replanned_repair_plan(
            repair_plan
        )
        self._validate_repair_review_plan(
            repair_review_plan
        )

        repair_context = self._repair_context(
            repair_execution_id=execution_id,
            resolution_record_id=resolution_id,
            attempt_number=attempt_number,
            repair_plan=repair_plan,
        )

        repair_context = {
            **repair_context,
            "repair_review_plan": (
                repair_review_plan.model_dump(
                    mode="json"
                )
            ),
        }

        operation_graph = (
            CustomerSupportOperationGraphBuilder()
            .build(
                review_plan_id=execution_id,
                review_plan=repair_review_plan,
                node_prefix="repair",
                idempotency_namespace=(
                    "support-repair"
                ),
                use_operation_ref_for_idempotency=(
                    True
                ),
                include_operation_metadata=True,
            )
        )

        nodes: list[dict] = [
            {
                "id": "trigger",
                "type": "custom",
                "data": {
                    "nodeType": "trigger.message",
                },
            },
            {
                "id": "extract_objective_repair",
                "type": "custom",
                "data": {
                    "nodeType": "context.extract",
                    "source": "extras",
                    "path": "objective_repair",
                    "save_as": "objective_repair",
                    "required": True,
                },
            },
            {
                "id": "repair_approval",
                "type": "custom",
                "data": {
                    "nodeType": "human.approval",
                    "question": (
                        "Approve execution of the rebuilt "
                        "customer-support repair operations?"
                    ),
                    "input_key": "resume_input",
                    "field": "approved",
                    "save_as": "repair_approval_result",
                    "context_key": "objective_repair",
                    "context_payload_key": (
                        "repair_context"
                    ),
                },
            },
            {
                "id": "route_repair_approval",
                "type": "custom",
                "data": {
                    "nodeType": "router.rules",
                    "rules": [
                        {
                            "when": (
                                "vars.repair_approval_result "
                                "== 'True'"
                            ),
                            "route": "approved",
                        }
                    ],
                    "default_route": "rejected",
                    "save_as": "repair_approval_route",
                },
            },
            {
                "id": "set_repair_rejected_result",
                "type": "custom",
                "data": {
                    "nodeType": "set.variable",
                    "key": "repair_result",
                    "value": {
                        "status": "rejected",
                        "repair_execution_id": (
                            execution_id
                        ),
                        "resolution_record_id": (
                            resolution_id
                        ),
                        "attempt_number": attempt_number,
                        "repair_request_ref": (
                            repair_plan
                            .repair_request_ref
                        ),
                        "controlling_disposition": (
                            repair_plan
                            .disposition.value
                        ),
                        "approval_granted": False,
                        "provider_mutation_performed": (
                            False
                        ),
                        "target_operation_refs": (
                            list(
                                repair_plan
                                .planned_target_refs
                            )
                        ),
                    },
                },
            },
            {
                "id": "rejected_repair_response",
                "type": "custom",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "repair_result",
                    "raw": True,
                },
            },
            {
                "id": "set_approved_repair_context",
                "type": "custom",
                "data": {
                    "nodeType": "set.variable",
                    "key": "approved_repair_context",
                    "save_as": (
                        "approved_repair_context"
                    ),
                    "value": {
                        "status": "provider_operations_completed",
                        "repair_execution_id": (
                            execution_id
                        ),
                        "resolution_record_id": (
                            resolution_id
                        ),
                        "attempt_number": attempt_number,
                        "repair_request_ref": (
                            repair_plan
                            .repair_request_ref
                        ),
                        "controlling_disposition": (
                            repair_plan
                            .disposition.value
                        ),
                        "approval_granted": True,
                        "provider_mutation_performed": (
                            True
                        ),
                        "target_operation_refs": (
                            list(
                                repair_plan
                                .planned_target_refs
                            )
                        ),
                    },
                },
            },
        ]

        nodes.extend(operation_graph.nodes)

        nodes.extend(
            [
                {
                    "id": "join_repair_operation_results",
                    "type": "custom",
                    "data": {
                        "nodeType": "join.all",
                        "mode": "object",
                        "save_as": (
                            "repair_operation_results"
                        ),
                    },
                },
                {
                    "id": "join_repair_result",
                    "type": "custom",
                    "data": {
                        "nodeType": "join.all",
                        "mode": "object",
                        "save_as": "repair_result",
                    },
                },
                {
                    "id": "approved_repair_response",
                    "type": "custom",
                    "data": {
                        "nodeType": "response",
                        "answer_from": "vars",
                        "answer_key": "repair_result",
                        "raw": True,
                    },
                },
            ]
        )

        edges: list[dict] = [
            {
                "source": "trigger",
                "target": "extract_objective_repair",
            },
            {
                "source": "extract_objective_repair",
                "target": "repair_approval",
            },
            {
                "source": "repair_approval",
                "target": "route_repair_approval",
            },
            {
                "source": "route_repair_approval",
                "target": "set_repair_rejected_result",
                "condition": "rejected",
            },
            {
                "source": "set_repair_rejected_result",
                "target": "rejected_repair_response",
            },
            {
                "source": "route_repair_approval",
                "target": "set_approved_repair_context",
                "condition": "approved",
            },
        ]

        for node_id in (
            operation_graph.entry_node_ids
        ):
            edges.append(
                {
                    "source": (
                        "set_approved_repair_context"
                    ),
                    "target": node_id,
                }
            )

        for node_id in (
            operation_graph.result_node_ids
        ):
            edges.append(
                {
                    "source": node_id,
                    "target": (
                        "join_repair_operation_results"
                    ),
                }
            )

        edges.extend(
            [
                {
                    "source": (
                        "set_approved_repair_context"
                    ),
                    "target": "join_repair_result",
                },
                {
                    "source": (
                        "join_repair_operation_results"
                    ),
                    "target": "join_repair_result",
                },
                {
                    "source": "join_repair_result",
                    "target": (
                        "approved_repair_response"
                    ),
                },
            ]
        )

        return {
            "name": (
                "Customer Support Replanned Repair "
                f"{execution_id}"
            ),
            "version": "1.0.0",
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "kind": (
                    "customer_support_objective_repair"
                ),
                "mode": (
                    "replanned_provider_operations"
                ),
                "repair_execution_id": execution_id,
                "resolution_record_id": resolution_id,
                "repair_request_ref": (
                    repair_plan.repair_request_ref
                ),
                "attempt_number": attempt_number,
                "controlling_disposition": (
                    repair_plan.disposition.value
                ),
                "automatic_execution_allowed": (
                    False
                ),
                "human_approval_required": True,
                "provider_mutation_allowed": True,
                "records_support_outcome": False,
                "delivers_customer_message": False,
                "objective_repair": repair_context,
            },
        }

    def build_non_mutating(
        self,
        *,
        repair_execution_id: str,
        resolution_record_id: str,
        attempt_number: int,
        repair_plan: ObjectiveRepairPlan,
    ) -> dict:
        execution_id = self._required(
            repair_execution_id,
            "repair_execution_id",
        )
        resolution_id = self._required(
            resolution_record_id,
            "resolution_record_id",
        )

        if attempt_number < 1:
            raise ValueError(
                "attempt_number must be >= 1"
            )

        if repair_plan.automatic_execution_allowed:
            raise ValueError(
                "Customer-support repair workflow cannot "
                "allow automatic execution"
            )

        if any(
            action.disposition
            in {
                ObjectiveRepairDisposition
                .REPLAN_REMAINING,
                ObjectiveRepairDisposition
                .RETRY_OPERATION,
            }
            for action in repair_plan.actions
        ):
            raise ValueError(
                "Non-mutating repair workflow cannot contain "
                "provider-operation repair actions"
            )

        repair_context = self._repair_context(
            repair_execution_id=execution_id,
            resolution_record_id=resolution_id,
            attempt_number=attempt_number,
            repair_plan=repair_plan,
        )

        nodes: list[dict] = [
            {
                "id": "trigger",
                "type": "custom",
                "data": {
                    "nodeType": "trigger.message",
                },
            },
            {
                "id": "extract_objective_repair",
                "type": "custom",
                "data": {
                    "nodeType": "context.extract",
                    "source": "extras",
                    "path": "objective_repair",
                    "save_as": "objective_repair",
                    "required": True,
                },
            },
        ]

        edges: list[dict] = [
            {
                "source": "trigger",
                "target": "extract_objective_repair",
            },
        ]

        previous_node_id = "extract_objective_repair"

        for sequence, action in enumerate(
            repair_plan.actions,
            start=1,
        ):
            node_id, node = self._action_node(
                sequence=sequence,
                action=action,
                repair_execution_id=execution_id,
                resolution_record_id=resolution_id,
                attempt_number=attempt_number,
            )

            nodes.append(node)
            edges.append(
                {
                    "source": previous_node_id,
                    "target": node_id,
                }
            )
            previous_node_id = node_id

        nodes.extend(
            [
                {
                    "id": "set_repair_control_result",
                    "type": "custom",
                    "data": {
                        "nodeType": "set.variable",
                        "key": "repair_control_result",
                        "value": {
                            "status": "control_completed",
                            "repair_execution_id": (
                                execution_id
                            ),
                            "resolution_record_id": (
                                resolution_id
                            ),
                            "attempt_number": (
                                attempt_number
                            ),
                            "repair_request_ref": (
                                repair_plan
                                .repair_request_ref
                            ),
                            "controlling_disposition": (
                                repair_plan
                                .disposition.value
                            ),
                            "automatic_execution": False,
                            "provider_mutation_performed": (
                                False
                            ),
                        },
                    },
                },
                {
                    "id": "repair_control_response",
                    "type": "custom",
                    "data": {
                        "nodeType": "response",
                        "answer_from": "vars",
                        "answer_key": (
                            "repair_control_result"
                        ),
                        "raw": True,
                    },
                },
            ]
        )

        edges.extend(
            [
                {
                    "source": previous_node_id,
                    "target": (
                        "set_repair_control_result"
                    ),
                },
                {
                    "source": (
                        "set_repair_control_result"
                    ),
                    "target": (
                        "repair_control_response"
                    ),
                },
            ]
        )

        return {
            "name": (
                "Customer Support Repair Control "
                f"{execution_id}"
            ),
            "version": "1.0.0",
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "kind": (
                    "customer_support_objective_repair"
                ),
                "mode": "non_mutating_control",
                "repair_execution_id": execution_id,
                "resolution_record_id": resolution_id,
                "repair_request_ref": (
                    repair_plan.repair_request_ref
                ),
                "attempt_number": attempt_number,
                "controlling_disposition": (
                    repair_plan.disposition.value
                ),
                "automatic_execution_allowed": (
                    False
                ),
                "provider_mutation_allowed": False,
                "objective_repair": repair_context,
            },
        }

    @staticmethod
    def objective_repair_extras(
        *,
        repair_execution_id: str,
        resolution_record_id: str,
        attempt_number: int,
        repair_plan: ObjectiveRepairPlan,
    ) -> dict:
        execution_id = (
            CustomerSupportRepairWorkflowBuilder
            ._required(
                repair_execution_id,
                "repair_execution_id",
            )
        )
        resolution_id = (
            CustomerSupportRepairWorkflowBuilder
            ._required(
                resolution_record_id,
                "resolution_record_id",
            )
        )

        if attempt_number < 1:
            raise ValueError(
                "attempt_number must be >= 1"
            )

        return (
            CustomerSupportRepairWorkflowBuilder
            ._repair_context(
                repair_execution_id=execution_id,
                resolution_record_id=resolution_id,
                attempt_number=attempt_number,
                repair_plan=repair_plan,
            )
        )

    @staticmethod
    def workflow_job_idempotency_key(
        *,
        repair_execution_id: str,
    ) -> str:
        execution_id = (
            CustomerSupportRepairWorkflowBuilder
            ._required(
                repair_execution_id,
                "repair_execution_id",
            )
        )

        return (
            "customer-support-repair-workflow:"
            f"{execution_id}:workflow-v1"
        )

    @classmethod
    def _action_node(
        cls,
        *,
        sequence: int,
        action: ObjectiveRepairAction,
        repair_execution_id: str,
        resolution_record_id: str,
        attempt_number: int,
    ) -> tuple[str, dict]:
        prefix = f"repair_action_{sequence:03d}"

        metadata = {
            "repair_action_ref": action.action_ref,
            "disposition": (
                action.disposition.value
            ),
            "target_operation_refs": list(
                action.target_operation_refs
            ),
            "reason_code": action.reason_code,
            "repair_execution_id": (
                repair_execution_id
            ),
            "resolution_record_id": (
                resolution_record_id
            ),
            "attempt_number": attempt_number,
            "source_task_id": (
                action.metadata.get(
                    "source_task_id"
                )
            ),
            "verification_ref": (
                action.metadata.get(
                    "verification_ref"
                )
            ),
        }

        if (
            action.disposition
            == ObjectiveRepairDisposition
            .WAIT_FOR_RESULT
        ):
            if not action.wait_for_event_type:
                raise ValueError(
                    "WAIT_FOR_RESULT repair action requires "
                    "wait_for_event_type"
                )

            if len(action.target_operation_refs) != 1:
                raise ValueError(
                    "Customer-support event wait requires "
                    "exactly one target operation"
                )

            operation_ref = (
                action.target_operation_refs[0]
            )

            node_id = f"{prefix}_wait"

            return node_id, {
                "id": node_id,
                "type": "custom",
                "data": {
                    "nodeType": "wait.event",
                    "event_type": (
                        action.wait_for_event_type
                    ),
                    "match": {
                        "repair_execution_id": (
                            repair_execution_id
                        ),
                        "resolution_record_id": (
                            resolution_record_id
                        ),
                        "operation_ref": operation_ref,
                    },
                    "reason": action.summary,
                    "metadata": metadata,
                },
            }

        if (
            action.disposition
            == ObjectiveRepairDisposition
            .REQUEST_HUMAN_ACTION
        ):
            if not action.human_approval_required:
                raise ValueError(
                    "Human repair action must require "
                    "human approval"
                )

            node_id = f"{prefix}_human_review"

            return node_id, {
                "id": node_id,
                "type": "custom",
                "data": {
                    "nodeType": "human.approval",
                    "question": action.summary,
                    "input_key": "resume_input",
                    "field": "approved",
                    "save_as": (
                        f"{prefix}_approved"
                    ),
                    "context_key": (
                        "objective_repair"
                    ),
                    "context_payload_key": (
                        "repair_context"
                    ),
                    "metadata": metadata,
                },
            }

        if (
            action.disposition
            == ObjectiveRepairDisposition.STOP_REPAIR
        ):
            node_id = f"{prefix}_stop"

            return node_id, {
                "id": node_id,
                "type": "custom",
                "data": {
                    "nodeType": "set.variable",
                    "key": f"{prefix}_result",
                    "value": {
                        "status": "repair_stopped",
                        "repair_action_ref": (
                            action.action_ref
                        ),
                        "target_operation_refs": (
                            list(
                                action
                                .target_operation_refs
                            )
                        ),
                        "reason_code": (
                            action.reason_code
                        ),
                        "summary": action.summary,
                        "provider_mutation_performed": (
                            False
                        ),
                    },
                    "metadata": metadata,
                },
            }

        raise ValueError(
            "Unsupported non-mutating customer-support "
            "repair disposition: "
            f"{action.disposition.value}"
        )

    @staticmethod
    def _validate_replanned_repair_plan(
        repair_plan: ObjectiveRepairPlan,
    ) -> None:
        if repair_plan.automatic_execution_allowed:
            raise ValueError(
                "Replanned customer-support repair "
                "cannot allow automatic execution"
            )

        if not repair_plan.human_approval_required:
            raise ValueError(
                "Replanned customer-support repair "
                "must require human approval"
            )

        if (
            repair_plan.disposition
            != ObjectiveRepairDisposition
            .REPLAN_REMAINING
        ):
            raise ValueError(
                "Replanned provider workflow requires "
                "REPLAN_REMAINING disposition"
            )

        if not repair_plan.actions:
            raise ValueError(
                "Replanned provider workflow requires "
                "repair actions"
            )

        invalid_actions = [
            action
            for action in repair_plan.actions
            if (
                action.disposition
                != ObjectiveRepairDisposition
                .REPLAN_REMAINING
            )
        ]

        if invalid_actions:
            raise ValueError(
                "Replanned provider workflow cannot "
                "contain non-replan repair actions"
            )

        if any(
            action.automatic_execution_allowed
            for action in repair_plan.actions
        ):
            raise ValueError(
                "Replanned repair actions cannot allow "
                "automatic execution"
            )

        if any(
            not action.human_approval_required
            for action in repair_plan.actions
        ):
            raise ValueError(
                "Every replanned repair action must "
                "require human approval"
            )

    @staticmethod
    def _validate_repair_review_plan(
        repair_review_plan: SupportReviewPlan,
    ) -> None:
        if not repair_review_plan.approval_required:
            raise ValueError(
                "Repair review plan must require "
                "human approval"
            )

        if repair_review_plan.execution_allowed:
            raise ValueError(
                "Repair review plan must remain "
                "execution-blocked before approval"
            )

        if not repair_review_plan.operations:
            raise ValueError(
                "Repair review plan requires operations"
            )

        operation_refs = [
            str(operation.operation_ref or "")
            .strip()
            for operation
            in repair_review_plan.operations
        ]

        if any(not ref for ref in operation_refs):
            raise ValueError(
                "Repair review operations must preserve "
                "original operation refs"
            )

        if len(operation_refs) != len(
            set(operation_refs)
        ):
            raise ValueError(
                "Repair review operations must have "
                "unique operation refs"
            )

    @staticmethod
    def _repair_context(
        *,
        repair_execution_id: str,
        resolution_record_id: str,
        attempt_number: int,
        repair_plan: ObjectiveRepairPlan,
    ) -> dict:
        return {
            "repair_execution_id": (
                repair_execution_id
            ),
            "resolution_record_id": (
                resolution_record_id
            ),
            "attempt_number": attempt_number,
            "repair_request_ref": (
                repair_plan.repair_request_ref
            ),
            "objective": (
                repair_plan.objective.model_dump(
                    mode="json"
                )
            ),
            "repair_plan": repair_plan.model_dump(
                mode="json"
            ),
        }

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
    "CustomerSupportRepairWorkflowBuilder",
]
