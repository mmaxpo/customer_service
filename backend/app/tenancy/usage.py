from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.tenancy.models import WorkspaceQuota, WorkspaceUsageEvent


class WorkspaceQuotaExceeded(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class WorkspaceRunAccessDenied(Exception):
    pass


@dataclass(frozen=True)
class RunAdmission:
    run_id: str
    max_total_tokens: int
    max_llm_calls: int
    max_tool_calls: int


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


class WorkspaceUsageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def begin_agent_run(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        run_id: str,
        requested_tokens: int | None,
        requested_llm_calls: int | None,
        requested_tool_calls: int | None,
    ) -> RunAdmission:
        result = await self.db.execute(
            select(WorkspaceQuota)
            .where(WorkspaceQuota.workspace_id == workspace_id)
            .with_for_update()
        )
        quota = result.scalar_one_or_none()
        if quota is None:
            quota = WorkspaceQuota(workspace_id=workspace_id)
            self.db.add(quota)
            await self.db.flush()

        totals = await self.db.execute(
            select(
                func.coalesce(func.sum(WorkspaceUsageEvent.total_tokens), 0),
                func.coalesce(
                    func.sum(WorkspaceUsageEvent.estimated_cost_microusd), 0
                ),
            ).where(
                WorkspaceUsageEvent.workspace_id == workspace_id,
                WorkspaceUsageEvent.created_at >= _month_start(),
            )
        )
        used_tokens, used_cost = totals.one()
        running = await self.db.scalar(
            select(func.count(WorkspaceUsageEvent.id)).where(
                WorkspaceUsageEvent.workspace_id == workspace_id,
                WorkspaceUsageEvent.status == "running",
            )
        )
        reason = None
        if int(used_tokens) >= quota.monthly_token_limit:
            reason = "monthly_token_quota_exceeded"
        elif int(used_cost) >= quota.monthly_cost_microusd_limit:
            reason = "monthly_cost_quota_exceeded"
        elif int(running or 0) >= quota.concurrent_run_limit:
            reason = "concurrent_run_quota_exceeded"

        if reason:
            self.db.add(
                WorkspaceUsageEvent(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    run_id=run_id,
                    kind="agent_run",
                    status="rejected",
                    rejection_reason=reason,
                )
            )
            await self.db.commit()
            raise WorkspaceQuotaExceeded(reason)

        self.db.add(
            WorkspaceUsageEvent(
                workspace_id=workspace_id,
                user_id=user_id,
                run_id=run_id,
                kind="agent_run",
                status="running",
            )
        )
        await self.db.commit()
        return RunAdmission(
            run_id=run_id,
            max_total_tokens=min(
                requested_tokens or quota.per_run_token_limit,
                quota.per_run_token_limit,
            ),
            max_llm_calls=min(
                requested_llm_calls or quota.per_run_llm_call_limit,
                quota.per_run_llm_call_limit,
            ),
            max_tool_calls=min(
                requested_tool_calls or quota.per_run_tool_call_limit,
                quota.per_run_tool_call_limit,
            ),
        )

    async def finish_agent_run(
        self,
        *,
        run_id: str,
        status: str,
        usage: dict | None = None,
        tool_calls: int = 0,
        rejection_reason: str | None = None,
    ) -> None:
        result = await self.db.execute(
            select(WorkspaceUsageEvent)
            .where(WorkspaceUsageEvent.run_id == run_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        usage = usage or {}
        row.status = status
        row.model = usage.get("model") or row.model
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        row.llm_calls += int(usage.get("llm_calls") or 0)
        row.tool_calls += tool_calls
        row.input_tokens += input_tokens
        row.output_tokens += output_tokens
        row.total_tokens += int(usage.get("total_tokens") or 0)
        row.estimated_cost_microusd += (
            input_tokens
            * settings.ESTIMATED_INPUT_MICROUSD_PER_MILLION_TOKENS
            + output_tokens
            * settings.ESTIMATED_OUTPUT_MICROUSD_PER_MILLION_TOKENS
        ) // 1_000_000
        row.rejection_reason = rejection_reason
        row.completed_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def resume_agent_run(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        run_id: str,
    ) -> RunAdmission:
        result = await self.db.execute(
            select(WorkspaceUsageEvent)
            .where(WorkspaceUsageEvent.run_id == run_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if (
            row is None
            or row.workspace_id != workspace_id
            or row.user_id != user_id
            or row.status != "paused"
        ):
            raise WorkspaceRunAccessDenied
        quota = await self.db.get(WorkspaceQuota, workspace_id)
        if quota is None:
            raise WorkspaceQuotaExceeded("workspace_quota_missing")
        row.status = "running"
        row.completed_at = None
        await self.db.commit()
        return RunAdmission(
            run_id=run_id,
            max_total_tokens=quota.per_run_token_limit,
            max_llm_calls=quota.per_run_llm_call_limit,
            max_tool_calls=quota.per_run_tool_call_limit,
        )

    async def assert_run_access(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        run_id: str,
    ) -> None:
        result = await self.db.execute(
            select(WorkspaceUsageEvent.id).where(
                WorkspaceUsageEvent.run_id == run_id,
                WorkspaceUsageEvent.workspace_id == workspace_id,
                WorkspaceUsageEvent.user_id == user_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise WorkspaceRunAccessDenied

    async def monthly_summary(self, *, workspace_id: UUID) -> dict:
        quota = await self.db.get(WorkspaceQuota, workspace_id)
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(WorkspaceUsageEvent.total_tokens), 0),
                func.coalesce(func.sum(WorkspaceUsageEvent.llm_calls), 0),
                func.coalesce(func.sum(WorkspaceUsageEvent.tool_calls), 0),
                func.coalesce(
                    func.sum(WorkspaceUsageEvent.estimated_cost_microusd), 0
                ),
                func.count(WorkspaceUsageEvent.id),
            ).where(
                WorkspaceUsageEvent.workspace_id == workspace_id,
                WorkspaceUsageEvent.created_at >= _month_start(),
            )
        )
        tokens, llm_calls, tool_calls, cost, runs = result.one()
        return {
            "period_start": _month_start(),
            "total_tokens": int(tokens),
            "llm_calls": int(llm_calls),
            "tool_calls": int(tool_calls),
            "estimated_cost_microusd": int(cost),
            "runs": int(runs),
            "quota": {
                "monthly_token_limit": quota.monthly_token_limit if quota else 0,
                "monthly_cost_microusd_limit": (
                    quota.monthly_cost_microusd_limit if quota else 0
                ),
            },
        }


__all__ = [
    "RunAdmission",
    "WorkspaceQuotaExceeded",
    "WorkspaceRunAccessDenied",
    "WorkspaceUsageService",
]
