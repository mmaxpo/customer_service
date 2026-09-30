from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Conversation,
    ConversationTag,
    Customer,
    CustomerServiceAuditLog,
    CustomerServiceConversationInsight,
    CustomerServiceCSATSurvey,
    CustomerServiceNotification,
    CustomerServiceProactiveIncident,
    CustomerServiceProactivePolicy,
    Ticket,
)
from app.domains.customer_service.schemas.proactive import ProactivePolicyWrite
from app.models.models import (
    CapabilityProviderHealthStateRecord,
    ObjectiveRepairExecutionRecord,
)
from app.platform.jobs.service import JobService
from app.tenancy.models import WorkspaceMembership


PROACTIVE_EVALUATION_JOB = "customer_service.proactive.evaluate"


class CustomerServiceProactivePlaybookService:
    def __init__(self, db: AsyncSession, *, workspace_id: UUID):
        self.db = db
        self.workspace_id = workspace_id

    async def seed_defaults(self):
        defaults = [
            ProactivePolicyWrite(signal="repeated_shipping_delays", threshold=2),
            ProactivePolicyWrite(signal="negative_csat", threshold=1),
            ProactivePolicyWrite(signal="vip_customer", threshold=1),
            ProactivePolicyWrite(signal="churn_chargeback_risk", threshold=1),
            ProactivePolicyWrite(
                signal="provider_outage", threshold=1, lookback_hours=24, cooldown_hours=4
            ),
            ProactivePolicyWrite(
                signal="repeated_failed_repairs", threshold=3, lookback_hours=168
            ),
        ]
        rows = [await self.upsert(payload) for payload in defaults]
        await self.schedule_next(minutes=1)
        return rows

    async def upsert(self, payload: ProactivePolicyWrite):
        row = await self.db.scalar(
            select(CustomerServiceProactivePolicy).where(
                CustomerServiceProactivePolicy.workspace_id == self.workspace_id,
                CustomerServiceProactivePolicy.signal == payload.signal,
            )
        )
        if row is None:
            row = CustomerServiceProactivePolicy(
                workspace_id=self.workspace_id, **payload.model_dump()
            )
            self.db.add(row)
        else:
            for key, value in payload.model_dump().items():
                setattr(row, key, value)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def list_policies(self):
        return list(
            await self.db.scalars(
                select(CustomerServiceProactivePolicy)
                .where(CustomerServiceProactivePolicy.workspace_id == self.workspace_id)
                .order_by(CustomerServiceProactivePolicy.signal)
            )
        )

    async def list_incidents(self, *, status: str | None, limit: int):
        statement = select(CustomerServiceProactiveIncident).where(
            CustomerServiceProactiveIncident.workspace_id == self.workspace_id
        )
        if status:
            statement = statement.where(CustomerServiceProactiveIncident.status == status)
        return list(
            await self.db.scalars(
                statement.order_by(CustomerServiceProactiveIncident.detected_at.desc()).limit(limit)
            )
        )

    async def resolve_incident(self, incident_id: UUID):
        row = await self.db.scalar(
            select(CustomerServiceProactiveIncident).where(
                CustomerServiceProactiveIncident.workspace_id == self.workspace_id,
                CustomerServiceProactiveIncident.id == incident_id,
            )
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Proactive incident not found")
        row.status = "resolved"
        row.resolved_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def evaluate(self) -> dict:
        policies = [row for row in await self.list_policies() if row.is_enabled]
        created = []
        for policy in policies:
            candidates = await self._candidates(policy)
            for candidate in candidates:
                incident = await self._trigger(policy, candidate)
                if incident is not None:
                    created.append(incident)
        await self.schedule_next(minutes=15)
        return {
            "evaluated_policies": len(policies),
            "incidents_created": len(created),
            "incident_ids": [str(row.id) for row in created],
        }

    async def schedule_next(self, *, minutes: int):
        run_after = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        slot = int(run_after.timestamp() // (15 * 60))
        await JobService(self.db).enqueue(
            user_id=self.workspace_id,
            job_type=PROACTIVE_EVALUATION_JOB,
            payload={"workspace_id": str(self.workspace_id)},
            run_after=run_after,
            max_attempts=3,
            idempotency_key=f"proactive-evaluation:{self.workspace_id}:{slot}",
        )

    async def _candidates(self, policy) -> list[dict]:
        since = datetime.now(timezone.utc) - timedelta(hours=policy.lookback_hours)
        if policy.signal == "negative_csat":
            rows = list(
                await self.db.scalars(
                    select(CustomerServiceCSATSurvey).where(
                        CustomerServiceCSATSurvey.workspace_id == self.workspace_id,
                        CustomerServiceCSATSurvey.answered_at >= since,
                        CustomerServiceCSATSurvey.score <= 2,
                    )
                )
            )
            return [
                {
                    "key": str(row.id),
                    "conversation_id": row.conversation_id,
                    "evidence": {"score": row.score, "survey_id": str(row.id)},
                    "severity": "high" if row.score == 1 else "medium",
                }
                for row in rows
            ]
        if policy.signal == "vip_customer":
            customers = list(
                await self.db.scalars(
                    select(Customer).where(Customer.user_id == self.workspace_id)
                )
            )
            result = []
            for customer in customers:
                fields = customer.custom_fields or {}
                is_vip = bool(fields.get("vip")) or fields.get("vip_tier") in {
                    "gold",
                    "platinum",
                }
                try:
                    lifetime_value = float(fields.get("lifetime_value") or 0)
                except (TypeError, ValueError):
                    lifetime_value = 0.0
                is_vip = is_vip or lifetime_value >= 1000
                if not is_vip:
                    continue
                conversation_id = await self.db.scalar(
                    select(Conversation.id)
                    .where(
                        Conversation.user_id == self.workspace_id,
                        Conversation.customer_id == customer.id,
                        Conversation.status.in_(["open", "pending"]),
                    )
                    .order_by(Conversation.updated_at.desc())
                    .limit(1)
                )
                if conversation_id:
                    result.append(
                        {
                            "key": str(customer.id),
                            "customer_id": customer.id,
                            "conversation_id": conversation_id,
                            "evidence": {"custom_fields": fields},
                            "severity": "medium",
                        }
                    )
            return result
        if policy.signal in {"repeated_shipping_delays", "churn_chargeback_risk"}:
            rows = (
                await self.db.execute(
                    select(CustomerServiceConversationInsight, Conversation).join(
                        Conversation,
                        Conversation.id == CustomerServiceConversationInsight.conversation_id,
                    ).where(
                        CustomerServiceConversationInsight.user_id == self.workspace_id,
                        CustomerServiceConversationInsight.updated_at >= since,
                    )
                )
            ).all()
            if policy.signal == "churn_chargeback_risk":
                return [
                    {
                        "key": str(conversation.id),
                        "customer_id": conversation.customer_id,
                        "conversation_id": conversation.id,
                        "evidence": {"risks": insight.risks, "intent": insight.intent},
                        "severity": "high",
                    }
                    for insight, conversation in rows
                    if "high" in (insight.risks or {}).values()
                ]
            grouped: dict[UUID, list[Conversation]] = {}
            for insight, conversation in rows:
                if insight.intent == "shipping_delay":
                    grouped.setdefault(conversation.customer_id, []).append(conversation)
            return [
                {
                    "key": str(customer_id),
                    "customer_id": customer_id,
                    "conversation_id": conversations[-1].id,
                    "evidence": {"delay_count": len(conversations)},
                    "severity": "high" if len(conversations) >= 3 else "medium",
                }
                for customer_id, conversations in grouped.items()
                if len(conversations) >= policy.threshold
            ]
        if policy.signal == "provider_outage":
            rows = list(
                await self.db.scalars(
                    select(CapabilityProviderHealthStateRecord).where(
                        CapabilityProviderHealthStateRecord.user_id == self.workspace_id,
                        CapabilityProviderHealthStateRecord.updated_at >= since,
                        CapabilityProviderHealthStateRecord.current_state != "healthy",
                    )
                )
            )
            return [
                {
                    "key": row.scope_key,
                    "provider_id": row.provider_id,
                    "evidence": {
                        "capability_id": row.capability_id,
                        "state": row.current_state,
                    },
                    "severity": "high",
                }
                for row in rows
            ]
        failed = int(
            await self.db.scalar(
                select(func.count(ObjectiveRepairExecutionRecord.id)).where(
                    ObjectiveRepairExecutionRecord.user_id == self.workspace_id,
                    ObjectiveRepairExecutionRecord.created_at >= since,
                    ObjectiveRepairExecutionRecord.status.in_(
                        ["failed", "blocked", "exhausted"]
                    ),
                )
            )
            or 0
        )
        return (
            [
                {
                    "key": "workspace",
                    "evidence": {"failed_repair_count": failed},
                    "severity": "high",
                }
            ]
            if failed >= policy.threshold
            else []
        )

    async def _trigger(self, policy, candidate: dict):
        bucket_seconds = policy.cooldown_hours * 3600
        bucket = int(datetime.now(timezone.utc).timestamp() // bucket_seconds)
        fingerprint = f"{policy.signal}:{candidate['key']}:{bucket}"
        existing = await self.db.scalar(
            select(CustomerServiceProactiveIncident.id).where(
                CustomerServiceProactiveIncident.workspace_id == self.workspace_id,
                CustomerServiceProactiveIncident.fingerprint == fingerprint,
            )
        )
        if existing:
            return None
        incident = CustomerServiceProactiveIncident(
            workspace_id=self.workspace_id,
            policy_id=policy.id,
            signal=policy.signal,
            fingerprint=fingerprint,
            severity=candidate["severity"],
            conversation_id=candidate.get("conversation_id"),
            customer_id=candidate.get("customer_id"),
            provider_id=candidate.get("provider_id"),
            evidence=candidate["evidence"],
        )
        try:
            async with self.db.begin_nested():
                self.db.add(incident)
                await self.db.flush()
        except IntegrityError:
            # Another evaluator won the same cooldown bucket. The unique
            # fingerprint is the final concurrency guard.
            return None
        incident.action_taken = await self._take_action(policy, incident)
        await self.db.commit()
        await self.db.refresh(incident)
        return incident

    async def _take_action(self, policy, incident) -> dict:
        action = policy.action or {}
        result = {"tagged": False, "priority": None, "notified": 0}
        if incident.conversation_id and action.get("tag", True):
            tag_name = f"proactive:{incident.signal}"
            existing = await self.db.scalar(
                select(ConversationTag.id).where(
                    ConversationTag.user_id == self.workspace_id,
                    ConversationTag.conversation_id == incident.conversation_id,
                    ConversationTag.name == tag_name,
                )
            )
            if existing is None:
                self.db.add(
                    ConversationTag(
                        user_id=self.workspace_id,
                        conversation_id=incident.conversation_id,
                        name=tag_name,
                    )
                )
            result["tagged"] = True
        priority = action.get("set_priority")
        if incident.conversation_id and priority:
            ticket = await self.db.scalar(
                select(Ticket).where(Ticket.conversation_id == incident.conversation_id)
            )
            if ticket:
                ticket.priority = priority
                result["priority"] = priority
        roles = action.get("notify_roles") or ["owner", "admin"]
        memberships = list(
            await self.db.scalars(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == self.workspace_id,
                    WorkspaceMembership.status == "active",
                    WorkspaceMembership.role.in_(roles),
                )
            )
        )
        for membership in memberships:
            self.db.add(
                CustomerServiceNotification(
                    workspace_id=self.workspace_id,
                    recipient_user_id=membership.user_id,
                    kind="proactive_alert",
                    entity_type="proactive_incident",
                    entity_id=incident.id,
                    payload={
                        "signal": incident.signal,
                        "severity": incident.severity,
                        "conversation_id": str(incident.conversation_id)
                        if incident.conversation_id
                        else None,
                    },
                )
            )
        result["notified"] = len(memberships)
        self.db.add(
            CustomerServiceAuditLog(
                user_id=self.workspace_id,
                entity_type="proactive_incident",
                entity_id=incident.id,
                action="proactive.incident_created",
                message=f"Detected {incident.signal}",
                meta={
                    "conversation_id": str(incident.conversation_id)
                    if incident.conversation_id
                    else None,
                    "signal": incident.signal,
                    "evidence": incident.evidence,
                },
            )
        )
        return result
