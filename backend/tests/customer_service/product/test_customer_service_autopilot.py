from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.domains.customer_service.schemas.autopilot import (
    AutopilotEvaluationRequest,
    AutopilotPolicyWrite,
)
from app.domains.customer_service.services.autopilot import (
    CustomerServiceAutopilotService,
)
from app.identity import create_user
from app.models.schemas import UserCreate
from app.tenancy.schemas import WorkspaceCreate
from app.tenancy.service import WorkspaceService


async def create_workspace(db):
    user = await create_user(
        UserCreate(
            email=f"autopilot-{uuid4()}@example.com",
            password=f"Autopilot-{uuid4()}",
            terms_accepted=True,
            terms_version="v1",
            privacy_accepted=True,
            privacy_version="v1",
        ),
        db,
    )
    workspace, _ = await WorkspaceService(db).create_workspace(
        user_id=user.id,
        payload=WorkspaceCreate(name=f"Autopilot {uuid4()}"),
    )
    return user, workspace


@pytest.mark.asyncio
async def test_autopilot_allows_safe_reply_but_never_auto_executes_mutation():
    async with SessionLocal() as db:
        user, workspace = await create_workspace(db)
        service = CustomerServiceAutopilotService(db)
        await service.upsert_policy(
            workspace_id=workspace.id,
            actor_user_id=user.id,
            payload=AutopilotPolicyWrite(
                intent="tracking_request",
                mode="auto_send_safe",
                minimum_confidence=0.8,
                maximum_auto_risk="low",
            ),
        )

        reply = await service.evaluate(
            workspace_id=workspace.id,
            payload=AutopilotEvaluationRequest(
                intent="tracking_request",
                action_kind="reply",
                confidence=0.94,
                risk="low",
                channel="email",
                language="en",
            ),
        )
        mutation = await service.evaluate(
            workspace_id=workspace.id,
            payload=AutopilotEvaluationRequest(
                intent="tracking_request",
                action_kind="mutation",
                confidence=0.99,
                risk="low",
                channel="email",
                language="en",
            ),
        )

        assert reply.decision == "auto_send_safe"
        assert reply.may_send is True
        assert mutation.decision == "require_approval"
        assert mutation.may_execute is False
        assert "mutation_requires_approval" in mutation.reason_codes


@pytest.mark.asyncio
async def test_autopilot_policy_is_workspace_scoped_and_defaults_safe():
    async with SessionLocal() as db:
        user_a, workspace_a = await create_workspace(db)
        _, workspace_b = await create_workspace(db)
        service = CustomerServiceAutopilotService(db)
        await service.upsert_policy(
            workspace_id=workspace_a.id,
            actor_user_id=user_a.id,
            payload=AutopilotPolicyWrite(
                intent="*", mode="auto_send_safe", minimum_confidence=0.8
            ),
        )
        request = AutopilotEvaluationRequest(
            intent="general_support",
            action_kind="reply",
            confidence=0.95,
            risk="low",
            channel="email",
            language="en",
        )

        decision_a = await service.evaluate(
            workspace_id=workspace_a.id, payload=request
        )
        decision_b = await service.evaluate(
            workspace_id=workspace_b.id, payload=request
        )

        assert decision_a.decision == "auto_send_safe"
        assert decision_b.decision == "draft_reply"
        assert decision_b.reason_codes == ["safe_default_no_policy"]
