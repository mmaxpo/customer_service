from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.identity import create_user
from app.models.schemas import UserCreate
from app.tenancy.models import WorkspaceQuota
from app.tenancy.repository import WorkspaceRepository
from app.tenancy.usage import WorkspaceQuotaExceeded, WorkspaceUsageService


@pytest.mark.asyncio
async def test_workspace_quota_clamps_run_and_records_cost():
    async with SessionLocal() as db:
        user = await create_user(
            UserCreate(
                email=f"usage-{uuid4()}@example.com",
                password=f"Usage-Password-{uuid4()}",
            ),
            db,
        )
        workspace = await WorkspaceRepository(db).get_personal_workspace_for_user(
            user_id=user.id
        )
        assert workspace is not None
        quota = await db.get(WorkspaceQuota, workspace.id)
        assert quota is not None
        quota.per_run_token_limit = 7
        quota.per_run_llm_call_limit = 2
        quota.per_run_tool_call_limit = 1
        quota.monthly_token_limit = 10
        await db.commit()

        usage = WorkspaceUsageService(db)
        run_id = str(uuid4())
        admission = await usage.begin_agent_run(
            workspace_id=workspace.id,
            user_id=user.id,
            run_id=run_id,
            requested_tokens=999,
            requested_llm_calls=999,
            requested_tool_calls=999,
        )
        assert admission.max_total_tokens == 7
        assert admission.max_llm_calls == 2
        assert admission.max_tool_calls == 1

        await usage.finish_agent_run(
            run_id=run_id,
            status="completed",
            usage={
                "model": "test-model",
                "llm_calls": 2,
                "tool_calls": 1,
                "input_tokens": 4,
                "output_tokens": 6,
                "total_tokens": 10,
            },
            tool_calls=1,
        )
        summary = await usage.monthly_summary(workspace_id=workspace.id)
        assert summary["total_tokens"] == 10
        assert summary["llm_calls"] == 2
        assert summary["tool_calls"] == 1
        assert summary["estimated_cost_microusd"] > 0

        with pytest.raises(
            WorkspaceQuotaExceeded,
            match="monthly_token_quota_exceeded",
        ):
            await usage.begin_agent_run(
                workspace_id=workspace.id,
                user_id=user.id,
                run_id=str(uuid4()),
                requested_tokens=None,
                requested_llm_calls=None,
                requested_tool_calls=None,
            )
