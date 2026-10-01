from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.services.conversation_intelligence_snapshot import (
    ConversationIntelligenceSnapshotService,
)
from app.domains.customer_service.services.suggested_actions import (
    SuggestedActionService,
)
from app.domains.customer_service.services.workflow_executions import (
    CustomerServiceWorkflowExecutionService,
)


class WorkspaceRecommendationsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_recommendations(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
    ) -> dict:
        snapshot = await ConversationIntelligenceSnapshotService(self.db).get_snapshot(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        suggested_actions = await SuggestedActionService(self.db).list(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        workflow_executions = await CustomerServiceWorkflowExecutionService(
            self.db
        ).list(
            user_id=user_id,
            conversation_id=conversation_id,
            limit=20,
            offset=0,
        )

        recommendations = self._build_recommendations(
            snapshot=snapshot,
            suggested_actions=suggested_actions,
            workflow_executions=workflow_executions,
        )

        priority = self._overall_priority(
            snapshot=snapshot,
            recommendations=recommendations,
        )

        return {
            "conversation_id": conversation_id,
            "priority": priority,
            "sla_risk": snapshot["sla_risk"],
            "customer_risk_level": snapshot["customer_risk_level"],
            "customer_risk_score": snapshot["customer_risk_score"],
            "recommended_actions": recommendations,
            "automation_candidates": self._automation_candidates(snapshot),
            "metadata": {
                "intent": snapshot["intent"],
                "urgency": snapshot["urgency"],
                "sentiment": snapshot["sentiment"],
                "open_ticket": snapshot["open_ticket"],
                "ticket_priority": snapshot["ticket_priority"],
                "suggested_action_count": len(suggested_actions),
                "workflow_execution_count": len(workflow_executions),
            },
        }

    def _build_recommendations(
        self,
        *,
        snapshot: dict,
        suggested_actions: list,
        workflow_executions: list[dict],
    ) -> list[dict]:
        rows: list[dict] = []

        if snapshot["sla_risk"]:
            rows.append(
                {
                    "type": "protect_sla",
                    "priority": "high",
                    "reason": "Open SLA target is breached or due soon.",
                    "payload": {"ticket_id": snapshot["metadata"].get("ticket_id")},
                }
            )

        if snapshot["customer_risk_level"] == "high":
            rows.append(
                {
                    "type": "assign_human_agent",
                    "priority": "high",
                    "reason": "Customer risk score is high.",
                    "payload": {"risk_score": snapshot["customer_risk_score"]},
                }
            )

        if snapshot["urgency"] == "high" or snapshot["sentiment"] == "negative":
            rows.append(
                {
                    "type": "reply_customer",
                    "priority": "high",
                    "reason": "Conversation has high urgency or negative sentiment.",
                    "payload": {
                        "urgency": snapshot["urgency"],
                        "sentiment": snapshot["sentiment"],
                    },
                }
            )

        for action in snapshot["recommended_actions"]:
            rows.append(
                {
                    "type": action,
                    "priority": "medium",
                    "reason": "Recommended by conversation intelligence snapshot.",
                    "payload": {"source": "conversation_intelligence_snapshot"},
                }
            )

        open_suggested = [
            action
            for action in suggested_actions
            if getattr(action, "status", None) == "suggested"
        ]

        if open_suggested:
            rows.append(
                {
                    "type": "review_suggested_actions",
                    "priority": "medium",
                    "reason": f"{len(open_suggested)} suggested action(s) are waiting for review.",
                    "payload": {
                        "suggested_action_ids": [
                            str(action.id) for action in open_suggested[:5]
                        ],
                    },
                }
            )

        if not workflow_executions and snapshot["intent"] in {
            "refund_request",
            "cancellation",
            "cancellation_request",
            "damaged_item",
            "shipping_delay",
            "tracking_request",
        }:
            rows.append(
                {
                    "type": "consider_workflow_automation",
                    "priority": "low",
                    "reason": "No workflow execution found for this automatable intent.",
                    "payload": {"intent": snapshot["intent"]},
                }
            )

        return self._dedupe(rows)

    def _automation_candidates(self, snapshot: dict) -> list[str]:
        intent = snapshot["intent"]

        mapping = {
            "refund_request": "refund_workflow",
            "cancellation": "cancellation_workflow",
            "cancellation_request": "cancellation_workflow",
            "damaged_item": "damaged_item_workflow",
            "shipping_delay": "shipping_status_workflow",
            "tracking_request": "shipping_status_workflow",
        }

        candidate = mapping.get(intent)
        return [candidate] if candidate else []

    def _overall_priority(self, *, snapshot: dict, recommendations: list[dict]) -> str:
        if any(row["priority"] == "high" for row in recommendations):
            return "high"

        if snapshot["customer_risk_level"] == "medium":
            return "medium"

        if any(row["priority"] == "medium" for row in recommendations):
            return "medium"

        return "low"

    def _dedupe(self, rows: list[dict]) -> list[dict]:
        seen = set()
        deduped = []

        for row in rows:
            key = row["type"]
            if key in seen:
                continue

            seen.add(key)
            deduped.append(row)

        return deduped
