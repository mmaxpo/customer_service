from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Conversation,
    CustomerServiceAuditLog,
    CustomerServiceConversationInsight,
    CustomerServiceCSATSurvey,
    CustomerServiceQualityReview,
    Ticket,
)
from app.models.models import PlatformJob, WorkflowWait
from app.tenancy.models import WorkspaceUsageEvent


class CustomerServiceBusinessValueAnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def report(self, *, workspace_id: UUID, days: int) -> dict:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        conversations = int(
            await self.db.scalar(
                select(func.count(Conversation.id)).where(
                    Conversation.user_id == workspace_id,
                    Conversation.created_at >= since,
                    Conversation.merged_into_id.is_(None),
                )
            )
            or 0
        )
        tickets = list(
            await self.db.scalars(
                select(Ticket).where(
                    Ticket.user_id == workspace_id,
                    Ticket.resolved_at.is_not(None),
                    Ticket.resolved_at >= since,
                )
            )
        )
        resolved = len(tickets)
        contained_ids = set(
            await self.db.scalars(
                select(CustomerServiceAuditLog.meta["conversation_id"].astext).where(
                    CustomerServiceAuditLog.user_id == workspace_id,
                    CustomerServiceAuditLog.created_at >= since,
                    CustomerServiceAuditLog.action == "autopilot.reply_sent",
                )
            )
        )
        contained_ids.discard(None)

        fcr = sum(
            bool((ticket.resolution_outcome or {}).get("resolved_on_first_contact"))
            for ticket in tickets
        )
        revenue_protected = sum(
            float((ticket.resolution_outcome or {}).get("revenue_protected") or 0)
            for ticket in tickets
        )
        refunds_prevented = sum(
            bool((ticket.resolution_outcome or {}).get("refund_prevented"))
            for ticket in tickets
        )
        refunds_prevented_amount = sum(
            float((ticket.resolution_outcome or {}).get("refund_prevented_amount") or 0)
            for ticket in tickets
        )

        waits = list(
            await self.db.scalars(
                select(WorkflowWait).where(
                    WorkflowWait.user_id == workspace_id,
                    WorkflowWait.wait_type == "approval",
                    WorkflowWait.created_at >= since,
                    WorkflowWait.resolved_at.is_not(None),
                )
            )
        )
        wait_seconds = [
            max(0.0, (wait.resolved_at - wait.created_at).total_seconds())
            for wait in waits
        ]

        reviews = list(
            await self.db.scalars(
                select(CustomerServiceQualityReview).where(
                    CustomerServiceQualityReview.user_id == workspace_id,
                    CustomerServiceQualityReview.created_at >= since,
                    CustomerServiceQualityReview.outcome.is_not(None),
                )
            )
        )
        accepted_without_edit = sum(
            review.outcome == "accepted_without_edit" for review in reviews
        )
        accepted_with_edit = sum(review.outcome == "accepted_with_edit" for review in reviews)
        accepted = accepted_without_edit + accepted_with_edit

        cost_microusd = int(
            await self.db.scalar(
                select(func.coalesce(func.sum(WorkspaceUsageEvent.estimated_cost_microusd), 0)).where(
                    WorkspaceUsageEvent.workspace_id == workspace_id,
                    WorkspaceUsageEvent.created_at >= since,
                )
            )
            or 0
        )

        provider_jobs = list(
            await self.db.scalars(
                select(PlatformJob.status).where(
                    PlatformJob.user_id == workspace_id,
                    PlatformJob.created_at >= since,
                    or_(
                        PlatformJob.job_type.ilike("%shopify%"),
                        PlatformJob.job_type.ilike("%omnichannel%"),
                        PlatformJob.job_type.ilike("%provider%"),
                    ),
                )
            )
        )
        provider_failures = sum(
            str(getattr(status, "value", status)) in {"failed", "dead_letter"}
            for status in provider_jobs
        )

        csat_by_intent, csat_by_workflow = await self._csat_breakdowns(
            workspace_id=workspace_id, since=since
        )
        return {
            "period_days": days,
            "conversations": conversations,
            "resolved_conversations": resolved,
            "automation_containment": self._rate(len(contained_ids), conversations),
            "first_contact_resolution": self._rate(fcr, resolved),
            "approval_waiting_seconds_average": (
                round(sum(wait_seconds) / len(wait_seconds), 2) if wait_seconds else None
            ),
            "cost_per_resolved_conversation_usd": (
                round(cost_microusd / 1_000_000 / resolved, 6) if resolved else None
            ),
            "ai_acceptance": self._rate(accepted, len(reviews)),
            "ai_accepted_without_edit": accepted_without_edit,
            "ai_accepted_with_edit": accepted_with_edit,
            "revenue_protected": round(revenue_protected, 2),
            "refunds_prevented": refunds_prevented,
            "refunds_prevented_amount": round(refunds_prevented_amount, 2),
            "provider_failure": self._rate(provider_failures, len(provider_jobs)),
            "csat_by_intent": csat_by_intent,
            "csat_by_workflow": csat_by_workflow,
        }

    async def _csat_breakdowns(
        self, *, workspace_id: UUID, since: datetime
    ) -> tuple[dict, dict]:
        surveys = list(
            await self.db.scalars(
                select(CustomerServiceCSATSurvey).where(
                    CustomerServiceCSATSurvey.workspace_id == workspace_id,
                    CustomerServiceCSATSurvey.answered_at >= since,
                    CustomerServiceCSATSurvey.score.is_not(None),
                )
            )
        )
        if not surveys:
            return {}, {}
        conversation_ids = {survey.conversation_id for survey in surveys}
        insights = list(
            await self.db.scalars(
                select(CustomerServiceConversationInsight)
                .where(
                    CustomerServiceConversationInsight.user_id == workspace_id,
                    CustomerServiceConversationInsight.conversation_id.in_(conversation_ids),
                )
                .order_by(CustomerServiceConversationInsight.updated_at.desc())
            )
        )
        latest = {}
        for insight in insights:
            latest.setdefault(insight.conversation_id, insight.intent)
        buckets: dict[str, list[int]] = {}
        workflow_jobs = list(
            await self.db.scalars(
                select(PlatformJob).where(
                    PlatformJob.user_id == workspace_id,
                    PlatformJob.created_at >= since,
                    PlatformJob.job_type == "workflow.run",
                )
            )
        )
        workflow_by_conversation = {}
        for job in workflow_jobs:
            payload = job.payload or {}
            extras = payload.get("extras") or {}
            event_payload = (extras.get("event") or {}).get("payload") or {}
            conversation_id = event_payload.get("conversation_id")
            workflow_name = (payload.get("workflow") or {}).get("name") or (
                extras.get("template") or {}
            ).get("name")
            if conversation_id and workflow_name:
                workflow_by_conversation.setdefault(str(conversation_id), workflow_name)
        workflow_buckets: dict[str, list[int]] = {}
        for survey in surveys:
            intent = latest.get(survey.conversation_id, "unknown")
            buckets.setdefault(intent, []).append(int(survey.score))
            workflow = workflow_by_conversation.get(
                str(survey.conversation_id), "no_workflow"
            )
            workflow_buckets.setdefault(workflow, []).append(int(survey.score))
        return self._score_buckets(buckets), self._score_buckets(workflow_buckets)

    def _score_buckets(self, buckets: dict[str, list[int]]) -> dict:
        return {
            intent: {
                "responses": len(scores),
                "average_score": round(sum(scores) / len(scores), 2),
            }
            for intent, scores in buckets.items()
        }

    def _rate(self, numerator: int, denominator: int) -> dict:
        return {
            "numerator": numerator,
            "denominator": denominator,
            "rate": round(numerator / denominator, 4) if denominator else None,
        }
