from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.routing_policies import (
    CustomerServiceRoutingPolicyRepository,
)
from app.domains.customer_service.schemas.routing_policies import (
    RoutingPolicyCreate,
    RoutingPolicyUpdate,
)
from app.domains.customer_service.services.routing_engine.engine import (
    CustomerServiceRoutingEngine,
)


class CustomerServiceRoutingPolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CustomerServiceRoutingPolicyRepository(db)

    async def create(self, *, user_id, payload: RoutingPolicyCreate):
        return await self.repo.create(
            user_id=user_id,
            name=payload.name,
            channel=payload.channel,
            intent=payload.intent,
            priority=payload.priority,
            strategy=payload.strategy,
            candidate_assignee_ids=payload.candidate_assignee_ids,
            candidate_team_ids=payload.candidate_team_ids,
            candidate_queue_ids=payload.candidate_queue_ids,
            priority_rank=payload.priority_rank,
            is_fallback=payload.is_fallback,
            is_active=payload.is_active,
            filters=payload.filters,
            meta=payload.meta,
        )

    async def list_for_user(self, *, user_id, active_only: bool | None = None):
        return await self.repo.list_for_user(
            user_id=user_id,
            active_only=active_only,
        )

    async def get(self, *, user_id, policy_id):
        policy = await self.repo.get(user_id=user_id, policy_id=policy_id)
        if policy is None:
            raise HTTPException(status_code=404, detail="Routing policy not found")
        return policy

    async def update(self, *, user_id, policy_id, payload: RoutingPolicyUpdate):
        policy = await self.get(user_id=user_id, policy_id=policy_id)
        return await self.repo.update(
            policy=policy,
            values=payload.model_dump(exclude_unset=True),
        )

    async def delete(self, *, user_id, policy_id):
        policy = await self.get(user_id=user_id, policy_id=policy_id)
        await self.repo.delete(policy=policy)
        return None

    async def route_event(
        self,
        *,
        user_id,
        event,
        workflow_result: dict | None = None,
    ) -> dict:
        payload = event.payload or {}

        conversation_id = payload.get("conversation_id")
        if not conversation_id:
            return {
                "routed": False,
                "reason": "event_missing_conversation_id",
            }

        body = payload.get("body") or ""
        channel = payload.get("channel")

        workflow_result = workflow_result or payload.get("workflow") or {}
        classification = workflow_result.get("classification") or {}
        action = workflow_result.get("action") or {}

        intent = classification.get("intent")
        priority = action.get("ticket_priority") or payload.get("priority")

        result = await CustomerServiceRoutingEngine(self.db).route_conversation(
            user_id=user_id,
            conversation_id=UUID(str(conversation_id)),
            channel=channel,
            body=body,
            intent=intent,
            priority=priority,
        )

        if result is None:
            return {
                "routed": False,
                "reason": "no_matching_routing_policy",
            }

        return {
            "routed": True,
            "policy_id": str(result["policy_id"]),
            "ticket_id": str(result["ticket_id"]),
            "assignment_id": str(result["assignment_id"])
            if result.get("assignment_id")
            else None,
            "assigned_to": str(result["assigned_to"]),
        }

    def _event_matches_policy_filters(
        self,
        *,
        policy_filters: dict,
        payload: dict,
    ) -> bool:
        if not policy_filters:
            return True

        keywords = policy_filters.get("keywords") or []
        if keywords:
            body = (payload.get("body") or "").lower()
            if not any(str(keyword).lower() in body for keyword in keywords):
                return False

        customer_email = policy_filters.get("customer_email")
        if customer_email:
            payload_email = (payload.get("customer_email") or "").lower()
            if payload_email != str(customer_email).lower():
                return False

        return True
