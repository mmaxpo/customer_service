from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.schemas.autopilot import (
    AutopilotDecisionRead,
    AutopilotEvaluationRequest,
    AutopilotPolicyRead,
    AutopilotPolicyWrite,
    ConversationAutopilotDecisionRequest,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal,
    require_customer_service_permission,
)
from app.domains.customer_service.services.autopilot import (
    CustomerServiceAutopilotService,
)


autopilot_router = APIRouter(tags=["Customer Service - Autopilot"])


@autopilot_router.get(
    "/autopilot/policies", response_model=list[AutopilotPolicyRead]
)
async def list_autopilot_policies(
    db: AsyncSession = Depends(get_db),
    principal=Depends(get_customer_service_principal),
):
    return await CustomerServiceAutopilotService(db).list_policies(
        workspace_id=principal.id
    )


@autopilot_router.put(
    "/autopilot/policies/{intent}", response_model=AutopilotPolicyRead
)
async def put_autopilot_policy(
    intent: str,
    payload: AutopilotPolicyWrite,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.autopilot.manage")),
):
    normalized = AutopilotPolicyWrite.model_validate(
        {**payload.model_dump(), "intent": intent}
    )
    return await CustomerServiceAutopilotService(db).upsert_policy(
        workspace_id=principal.id,
        actor_user_id=principal.actor_user_id,
        payload=normalized,
    )


@autopilot_router.post(
    "/autopilot/policies/seed-safe-defaults",
    response_model=list[AutopilotPolicyRead],
)
async def seed_safe_autopilot_policies(
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.autopilot.manage")),
):
    return await CustomerServiceAutopilotService(db).seed_safe_defaults(
        workspace_id=principal.id,
        actor_user_id=principal.actor_user_id,
    )


@autopilot_router.delete(
    "/autopilot/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_autopilot_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.autopilot.manage")),
):
    await CustomerServiceAutopilotService(db).delete_policy(
        workspace_id=principal.id, policy_id=policy_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@autopilot_router.post(
    "/autopilot/evaluate", response_model=AutopilotDecisionRead
)
async def evaluate_autopilot(
    payload: AutopilotEvaluationRequest,
    db: AsyncSession = Depends(get_db),
    principal=Depends(get_customer_service_principal),
):
    return await CustomerServiceAutopilotService(db).evaluate(
        workspace_id=principal.id, payload=payload
    )


@autopilot_router.post(
    "/conversations/{conversation_id}/autopilot/decision",
    response_model=AutopilotDecisionRead,
)
async def evaluate_conversation_autopilot(
    conversation_id: UUID,
    payload: ConversationAutopilotDecisionRequest,
    db: AsyncSession = Depends(get_db),
    principal=Depends(get_customer_service_principal),
):
    return await CustomerServiceAutopilotService(db).evaluate_conversation(
        workspace_id=principal.id,
        actor_user_id=principal.actor_user_id,
        conversation_id=conversation_id,
        payload=payload,
    )


__all__ = ["autopilot_router"]
