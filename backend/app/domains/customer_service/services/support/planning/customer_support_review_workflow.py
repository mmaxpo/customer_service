from __future__ import annotations

from app.domains.customer_service.services.support.planning.customer_support_operation_graph import (
    CustomerSupportOperationGraphBuilder,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewPlan,
)


class CustomerSupportReviewWorkflowBuilder:
    """
    Convert an immutable support review plan into a durable approval workflow.

    Safety rules:
    - Human approval always occurs before provider capability invocation.
    - Every provider operation receives its own deterministic idempotency key.
    - Replacement address is embedded in the replacement shipment scope.
    - No mutation is performed while this workflow is being constructed.
    """

    def build(
        self,
        *,
        review_plan_id: str,
        review_plan: SupportReviewPlan,
    ) -> dict:
        normalized_plan_id = str(review_plan_id or "").strip()

        if not normalized_plan_id:
            raise ValueError("review_plan_id is required")

        if not review_plan.approval_required:
            raise ValueError(
                "Support review workflow requires approval_required=True"
            )

        if review_plan.execution_allowed:
            raise ValueError(
                "Review plan must remain execution-blocked before approval"
            )

        try:
            operation_graph = (
                CustomerSupportOperationGraphBuilder()
                .build(
                    review_plan_id=normalized_plan_id,
                    review_plan=review_plan,
                    idempotency_namespace=(
                        "support-review"
                    ),
                    use_operation_ref_for_idempotency=(
                        False
                    ),
                    include_operation_metadata=False,
                )
            )
        except ValueError as exc:
            if (
                "no executable provider operation"
                in str(exc)
            ):
                raise ValueError(
                    "Review plan contains no executable "
                    "preparation operation"
                ) from exc

            raise

        approval_context = {
            "review_plan_id": normalized_plan_id,
            "review_plan": review_plan.model_dump(mode="json"),
        }

        nodes: list[dict] = [
            {
                "id": "trigger",
                "type": "custom",
                "data": {
                    "nodeType": "trigger.message",
                },
            },
            {

                "id": "capture_customer_chat_session",

                "type": "custom",

                "data": {

                    "nodeType": "context.extract",

                    "source": "event_payload",

                    "path": "session_id",

                    "save_as": "customer_chat_session_id",

                    "required": True,

                },

            },

            {
                "id": "extract_support_review",
                "type": "custom",
                "data": {
                    "nodeType": "context.extract",
                    "source": "extras",
                    "path": "support_review",
                    "save_as": "support_review",
                },
            },
            {
                "id": "approval",
                "type": "custom",
                "data": {
                    "nodeType": "human.approval",
                    "question": (
                        "Approve this customer-support resolution plan?"
                    ),
                    "context_key": "support_review",
                    "context_payload_key": "context",
                    "save_as": "approval_result",
                },
            },
            {
                "id": "route_approval",
                "type": "custom",
                "data": {
                    "nodeType": "router.rules",
                    "rules": [
                        {
                            "when": (
                                "vars.approval_result == 'True'"
                            ),
                            "route": "approved",
                        }
                    ],
                    "default_route": "rejected",
                    "save_as": "approval_route",
                },
            },
            {
                "id": "set_rejected_result",
                "type": "custom",
                "data": {
                    "nodeType": "set.variable",
                    "key": "review_result",
                    "value": {
                        "status": "rejected",
                        "review_plan_id": normalized_plan_id,
                        "message": (
                            "The support resolution plan was rejected. "
                            "No Shopify action was performed."
                        ),
                        "operations": [],
                    },
                },
            },
            {
                "id": "project_rejected_outcome",
                "type": "custom",
                "data": {
                    "nodeType": (
                        "customer_service."
                        "project_support_outcome"
                    ),
                    "save_as": "support_outcome",
                    "message_save_as": "customer_message",
                },
            },
            {
                "id": "record_rejected_outcome",
                "type": "custom",
                "data": {
                    "nodeType": "customer_service.record_support_outcome",
                    "save_as": "recorded_support_outcome",
                },
            },
            {
                "id": "reply_rejected_outcome",
                "type": "custom",
                "data": {
                    "nodeType": "reply.customer_chat",
                    "session_id_from": "vars",
                    "session_id_key": "customer_chat_session_id",
                    "message_from": "vars",
                    "message_key": "customer_message",
                    "save_as": "customer_outcome_delivery",
                },
            },
            {
                "id": "rejected_response",
                "type": "custom",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "support_outcome",
                    "raw": True,
                },
            },
        ]

        edges: list[dict] = [
            {

                "source": "trigger",

                "target": "capture_customer_chat_session",

            },

            {

                "source": "capture_customer_chat_session",

                "target": "extract_support_review",

            },

            {
                "source": "extract_support_review",
                "target": "approval",
            },
            {
                "source": "approval",
                "target": "route_approval",
            },
            {
                "source": "route_approval",
                "target": "set_rejected_result",
                "condition": "rejected",
            },
            {
                "source": "set_rejected_result",
                "target": "project_rejected_outcome",
            },
            {
                "source": "project_rejected_outcome",
                "target": "record_rejected_outcome",
            },
            {
                "source": "record_rejected_outcome",
                "target": "reply_rejected_outcome",
            },
            {
                "source": "reply_rejected_outcome",
                "target": "rejected_response",
            },
        ]

        nodes.extend(
            operation_graph.nodes
        )

        for node_id in (
            operation_graph.entry_node_ids
        ):
            edges.append(
                {
                    "source": "route_approval",
                    "target": node_id,
                    "condition": "approved",
                }
            )

        nodes.extend(
            [
                {
                    "id": "join_preparation_results",
                    "type": "custom",
                    "data": {
                        "nodeType": "join.all",
                        "mode": "object",
                        "save_as": "prepared_operations",
                    },
                },
                {
                    "id": "project_approved_outcome",
                    "type": "custom",
                    "data": {
                        "nodeType": (
                            "customer_service."
                            "project_support_outcome"
                        ),
                        "save_as": "support_outcome",
                        "message_save_as": "customer_message",
                    },
                },
                {
                    "id": "record_approved_outcome",
                    "type": "custom",
                    "data": {
                        "nodeType": "customer_service.record_support_outcome",
                        "save_as": "recorded_support_outcome",
                    },
                },
                {
                    "id": "reply_approved_outcome",
                    "type": "custom",
                    "data": {
                        "nodeType": "reply.customer_chat",
                        "session_id_from": "vars",
                        "session_id_key": "customer_chat_session_id",
                        "message_from": "vars",
                        "message_key": "customer_message",
                        "save_as": "customer_outcome_delivery",
                    },
                },
                {
                    "id": "approved_response",
                    "type": "custom",
                    "data": {
                        "nodeType": "response",
                        "answer_from": "vars",
                        "answer_key": "support_outcome",
                        "raw": True,
                    },
                },
            ]
        )

        for node_id in (
            operation_graph.result_node_ids
        ):
            edges.append(
                {
                    "source": node_id,
                    "target": "join_preparation_results",
                }
            )

        edges.extend(
            [
                {
                    "source": "join_preparation_results",
                    "target": "project_approved_outcome",
                },
                {
                    "source": "project_approved_outcome",
                    "target": "record_approved_outcome",
                },
                {
                    "source": "record_approved_outcome",
                    "target": "reply_approved_outcome",
                },
                {
                    "source": "reply_approved_outcome",
                    "target": "approved_response",
                },
            ]
        )

        return {
            "name": (
                "Customer Support Review "
                f"{normalized_plan_id}"
            ),
            "version": "1.0.0",
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "kind": "customer_support_review",
                "review_plan_id": normalized_plan_id,
                "approval_required": True,
                "provider": review_plan.provider,
                "order_ref": review_plan.order_ref,
                "support_review": approval_context,
            },
        }

    @staticmethod
    def support_review_extras(
        *,
        review_plan_id: str,
        review_plan: SupportReviewPlan,
    ) -> dict:
        return {
            "review_plan_id": str(review_plan_id),
            "review_plan": review_plan.model_dump(mode="json"),
        }

    @staticmethod
    def workflow_job_idempotency_key(
        *,
        review_plan_id: str,
    ) -> str:
        return (
            "customer-support-review-workflow:"
            f"{str(review_plan_id).strip()}:v1"
        )
