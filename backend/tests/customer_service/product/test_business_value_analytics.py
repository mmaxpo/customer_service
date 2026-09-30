from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    CustomerServiceAuditLog,
    CustomerServiceConversationInsight,
    CustomerServiceCSATSurvey,
    CustomerServiceQualityReview,
    Ticket,
)
from app.domains.customer_service.services.business_value_analytics import (
    CustomerServiceBusinessValueAnalyticsService,
)
from app.models.models import PlatformJob, WorkflowWait
from app.tenancy.models import WorkspaceUsageEvent
from tests.customer_service.product.test_helpdesk_table_stakes import helpdesk_context


@pytest.mark.asyncio
async def test_business_value_report_uses_durable_product_and_runtime_truth():
    async with SessionLocal() as db:
        user, workspace, _, conversation = await helpdesk_context(db)
        ticket = await db.scalar(
            select(Ticket).where(Ticket.conversation_id == conversation.id)
        )
        now = datetime.now(timezone.utc)
        ticket.resolved_at = now
        ticket.status = "closed"
        ticket.resolution_outcome = {
            "resolved_on_first_contact": True,
            "revenue_protected": 80,
            "refund_prevented": True,
            "refund_prevented_amount": 25,
        }
        db.add_all(
            [
                CustomerServiceAuditLog(
                    user_id=workspace.id,
                    actor_id=user.id,
                    entity_type="suggested_action",
                    entity_id=uuid4(),
                    action="autopilot.reply_sent",
                    meta={"conversation_id": str(conversation.id)},
                ),
                CustomerServiceQualityReview(
                    user_id=workspace.id,
                    conversation_id=conversation.id,
                    overall_score=5,
                    outcome="accepted_without_edit",
                ),
                CustomerServiceConversationInsight(
                    user_id=workspace.id,
                    conversation_id=conversation.id,
                    sentiment="neutral",
                    intent="tracking_request",
                    urgency="normal",
                    summary="Tracking question",
                    confidence=0.95,
                    source="rule",
                    language="en",
                ),
                CustomerServiceCSATSurvey(
                    workspace_id=workspace.id,
                    conversation_id=conversation.id,
                    ticket_id=ticket.id,
                    token_hash=uuid4().hex,
                    status="answered",
                    score=5,
                    answered_at=now,
                ),
                WorkflowWait(
                    user_id=workspace.id,
                    workflow_run_id=str(uuid4()),
                    wait_type="approval",
                    status="approved",
                    payload={},
                    created_at=now - timedelta(minutes=2),
                    resolved_at=now,
                ),
                WorkspaceUsageEvent(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    run_id=f"analytics-{uuid4()}",
                    kind="customer_service",
                    status="completed",
                    estimated_cost_microusd=500_000,
                ),
                PlatformJob(
                    user_id=workspace.id,
                    job_type="shopify.provider.call",
                    status="dead_letter",
                    payload={},
                    attempts=3,
                    max_attempts=3,
                ),
            ]
        )
        await db.commit()

        report = await CustomerServiceBusinessValueAnalyticsService(db).report(
            workspace_id=workspace.id, days=30
        )

        assert report["automation_containment"]["rate"] == 1.0
        assert report["first_contact_resolution"]["rate"] == 1.0
        assert report["approval_waiting_seconds_average"] == 120.0
        assert report["cost_per_resolved_conversation_usd"] == 0.5
        assert report["ai_acceptance"]["rate"] == 1.0
        assert report["provider_failure"]["rate"] == 1.0
        assert report["revenue_protected"] == 80.0
        assert report["refunds_prevented"] == 1
        assert report["csat_by_intent"]["tracking_request"]["average_score"] == 5.0

