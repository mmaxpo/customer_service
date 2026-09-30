from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Conversation,
    CustomerServiceAutopilotPolicy,
)
from app.domains.customer_service.repositories.audit_logs import AuditLogRepository
from app.domains.customer_service.schemas.autopilot import (
    AutopilotDecisionRead,
    AutopilotEvaluationRequest,
    AutopilotPolicyWrite,
    ConversationAutopilotDecisionRequest,
)
from app.domains.customer_service.services.conversation_intelligence import (
    ConversationIntelligenceService,
)


_RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class CustomerServiceAutopilotService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_policies(self, *, workspace_id: UUID):
        result = await self.db.execute(
            select(CustomerServiceAutopilotPolicy)
            .where(CustomerServiceAutopilotPolicy.workspace_id == workspace_id)
            .order_by(CustomerServiceAutopilotPolicy.intent)
        )
        return list(result.scalars().all())

    async def seed_safe_defaults(
        self, *, workspace_id: UUID, actor_user_id: UUID
    ) -> list[CustomerServiceAutopilotPolicy]:
        defaults = [
            AutopilotPolicyWrite(intent="*", mode="draft_reply"),
            AutopilotPolicyWrite(
                intent="tracking_request",
                mode="auto_send_safe",
                minimum_confidence=0.92,
                maximum_auto_risk="low",
            ),
            AutopilotPolicyWrite(
                intent="product_question",
                mode="auto_send_safe",
                minimum_confidence=0.94,
                maximum_auto_risk="low",
            ),
            AutopilotPolicyWrite(intent="refund_request", mode="require_approval"),
            AutopilotPolicyWrite(
                intent="cancellation_request", mode="require_approval"
            ),
            AutopilotPolicyWrite(intent="damaged_item", mode="require_approval"),
        ]
        return [
            await self.upsert_policy(
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                payload=payload,
            )
            for payload in defaults
        ]

    async def upsert_policy(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        payload: AutopilotPolicyWrite,
    ):
        policy = await self._find_policy(
            workspace_id=workspace_id, intent=payload.intent, include_default=False
        )
        values = payload.model_dump()
        if policy is None:
            policy = CustomerServiceAutopilotPolicy(
                workspace_id=workspace_id,
                created_by_user_id=actor_user_id,
                **values,
            )
            self.db.add(policy)
        else:
            for key, value in values.items():
                setattr(policy, key, value)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def delete_policy(self, *, workspace_id: UUID, policy_id: UUID) -> None:
        policy = await self.db.scalar(
            select(CustomerServiceAutopilotPolicy).where(
                CustomerServiceAutopilotPolicy.workspace_id == workspace_id,
                CustomerServiceAutopilotPolicy.id == policy_id,
            )
        )
        if policy is None:
            raise HTTPException(status_code=404, detail="Autopilot policy not found")
        await self.db.delete(policy)
        await self.db.commit()

    async def evaluate(
        self, *, workspace_id: UUID, payload: AutopilotEvaluationRequest
    ) -> AutopilotDecisionRead:
        policy = await self._find_policy(
            workspace_id=workspace_id, intent=payload.intent, include_default=True
        )
        if policy is None:
            return self._default_decision(payload)
        return self._apply(policy, payload)

    async def evaluate_conversation(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        conversation_id: UUID,
        payload: ConversationAutopilotDecisionRequest,
    ) -> AutopilotDecisionRead:
        conversation = await self.db.scalar(
            select(Conversation).where(
                Conversation.user_id == workspace_id,
                Conversation.id == conversation_id,
            )
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        insight = await ConversationIntelligenceService(self.db).analyze(
            user_id=workspace_id,
            conversation_id=conversation_id,
            force_refresh=payload.force_refresh_intelligence,
        )
        request = AutopilotEvaluationRequest(
            intent=insight.intent,
            action_kind=payload.action_kind,
            risk=payload.risk,
            confidence=insight.confidence or 0,
            channel=payload.channel or conversation.channel,
            language=getattr(insight, "language", None) or "und",
            action_type=payload.action_type,
        )
        decision = await self.evaluate(workspace_id=workspace_id, payload=request)
        await AuditLogRepository(self.db).create(
            user_id=workspace_id,
            actor_id=actor_user_id,
            entity_type="conversation",
            entity_id=conversation_id,
            action="autopilot.decision",
            message=f"Autopilot chose {decision.decision} for {insight.intent}",
            meta={
                "conversation_id": str(conversation_id),
                "intent": insight.intent,
                "policy_id": str(decision.policy_id) if decision.policy_id else None,
                "decision": decision.model_dump(mode="json"),
            },
        )
        return decision

    async def _find_policy(
        self, *, workspace_id: UUID, intent: str, include_default: bool
    ):
        intents = [intent.strip().lower()]
        if include_default:
            intents.append("*")
        result = await self.db.execute(
            select(CustomerServiceAutopilotPolicy).where(
                CustomerServiceAutopilotPolicy.workspace_id == workspace_id,
                CustomerServiceAutopilotPolicy.intent.in_(intents),
            )
        )
        policies = {row.intent: row for row in result.scalars().all()}
        return policies.get(intents[0]) or policies.get("*")

    def _default_decision(
        self, payload: AutopilotEvaluationRequest
    ) -> AutopilotDecisionRead:
        decision = "require_approval" if payload.action_kind == "mutation" else "draft_reply"
        return self._decision(
            payload=payload,
            policy=None,
            matched_intent="*",
            requested_mode="draft_reply",
            decision=decision,
            reasons=["safe_default_no_policy"],
        )

    def _apply(
        self,
        policy: CustomerServiceAutopilotPolicy,
        payload: AutopilotEvaluationRequest,
    ) -> AutopilotDecisionRead:
        reasons: list[str] = []
        decision = policy.mode
        if not policy.is_enabled or policy.mode == "never_automate":
            decision = "never_automate"
            reasons.append("policy_disabled_or_never")
        elif payload.channel.lower() not in policy.allowed_channels:
            decision = "recommend_only"
            reasons.append("channel_not_allowed")
        elif "*" not in policy.allowed_languages and payload.language.lower() not in policy.allowed_languages:
            decision = "draft_reply"
            reasons.append("language_not_allowed")
        elif payload.confidence < policy.minimum_confidence:
            decision = "draft_reply"
            reasons.append("confidence_below_threshold")
        elif _RISK_RANK[payload.risk] > _RISK_RANK[policy.maximum_auto_risk]:
            decision = "require_approval"
            reasons.append("risk_above_policy_limit")

        # Commerce mutations can never be sent or executed directly from a model
        # decision. This invariant remains true even if a merchant misconfigures
        # a policy or a frontend submits an unsafe mode.
        if (
            decision != "never_automate"
            and payload.action_kind == "mutation"
            and policy.mutation_requires_approval
        ):
            decision = "require_approval"
            reasons.append("mutation_requires_approval")

        if not reasons:
            reasons.append("policy_matched")
        return self._decision(
            payload=payload,
            policy=policy,
            matched_intent=policy.intent,
            requested_mode=policy.mode,
            decision=decision,
            reasons=list(dict.fromkeys(reasons)),
        )

    def _decision(
        self,
        *,
        payload: AutopilotEvaluationRequest,
        policy,
        matched_intent: str,
        requested_mode: str,
        decision: str,
        reasons: list[str],
    ) -> AutopilotDecisionRead:
        may_send = decision == "auto_send_safe" and payload.action_kind == "reply"
        may_execute = decision == "auto_send_safe" and payload.action_kind != "mutation"
        return AutopilotDecisionRead(
            policy_id=policy.id if policy else None,
            matched_intent=matched_intent,
            requested_mode=requested_mode,
            decision=decision,
            may_send=may_send,
            may_execute=may_execute,
            requires_approval=decision == "require_approval",
            reason_codes=reasons,
            confidence=payload.confidence,
            risk=payload.risk,
            action_kind=payload.action_kind,
            channel=payload.channel,
            language=payload.language,
        )
