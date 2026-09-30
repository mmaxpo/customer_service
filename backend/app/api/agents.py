from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_runtime.runner import AgentRuntimeContext
from app.agents_runtime.services import (
    AgentRuntimeServices,
    build_agent_runtime_services,
)
from app.agents_runtime.usage.budget import UsageBudget
from app.core.session import get_db
from app.tenancy.context import Principal, get_current_principal
from app.tenancy.usage import (
    WorkspaceQuotaExceeded,
    WorkspaceRunAccessDenied,
    WorkspaceUsageService,
)

router = APIRouter(prefix="/agents", tags=["agents"])


def _validate_agent_run_id(agent_run_id: str) -> None:
    try:
        UUID(agent_run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent_run_id")


class AgentRunRequest(BaseModel):
    input: str = Field(..., min_length=1)
    tools: list[str] = Field(default_factory=list)
    system_prompt: str = "You are a careful AI agent. Use tools when needed."
    max_steps: int | None = Field(default=None, ge=1, le=50)
    max_total_tokens: int | None = Field(default=None, ge=1)
    max_llm_calls: int | None = Field(default=None, ge=1)
    max_tool_calls: int | None = Field(default=None, ge=1)


class AgentApproveRequest(BaseModel):
    approved: bool
    reason: str | None = None
    tools: list[str] = Field(default_factory=list)


def get_agent_services(request: Request) -> AgentRuntimeServices:
    services = getattr(request.app.state, "agent_runtime_services", None)

    if services is None:
        services = build_agent_runtime_services()
        request.app.state.agent_runtime_services = services

    return services


TERMINAL_STREAM_EVENTS = {
    "run_completed",
    "run_failed",
    "approval_required",
}


def _is_terminal_stream_event(event) -> bool:
    return str(event.type) in TERMINAL_STREAM_EVENTS


@router.post("/run")
async def run_agent(
    request: Request,
    body: AgentRunRequest,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    services = get_agent_services(request)
    context = AgentRuntimeContext(user_id=str(principal.user_id))
    usage_service = WorkspaceUsageService(db)
    try:
        admission = await usage_service.begin_agent_run(
            workspace_id=principal.workspace_id,
            user_id=principal.user_id,
            run_id=context.agent_run_id,
            requested_tokens=body.max_total_tokens,
            requested_llm_calls=body.max_llm_calls,
            requested_tool_calls=body.max_tool_calls,
        )
    except WorkspaceQuotaExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail={"code": exc.reason},
        ) from None

    try:
        state, recorder = await services.runner.run(
            user_input=body.input,
            system_prompt=body.system_prompt,
            tool_names=body.tools,
            context=context,
            usage_budget=UsageBudget(
                max_total_tokens=admission.max_total_tokens,
                max_llm_calls=admission.max_llm_calls,
                max_tool_calls=admission.max_tool_calls,
            ),
            max_steps=min(
                body.max_steps or services.runner.max_steps,
                admission.max_tool_calls + admission.max_llm_calls,
            ),
        )
    except Exception:
        await usage_service.finish_agent_run(
            run_id=context.agent_run_id,
            status="failed",
            rejection_reason="runtime_exception",
        )
        raise

    usage = state.meta.get("usage") or {}
    await usage_service.finish_agent_run(
        run_id=context.agent_run_id,
        status=str(state.status),
        usage=usage,
        tool_calls=int(usage.get("tool_calls") or 0),
    )

    return {
        "agent_run_id": state.agent_run_id,
        "status": state.status,
        "steps": state.steps,
        "final_output": state.final_output,
        "pending_approval": (
            state.pending_approval.model_dump() if state.pending_approval else None
        ),
        "errors": [error.model_dump() for error in state.errors],
        "events": [event.model_dump(mode="json") for event in recorder.events],
    }


@router.get("/runs/{agent_run_id}/events")
async def list_agent_events(
    request: Request,
    agent_run_id: str,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    _validate_agent_run_id(agent_run_id)

    try:
        await WorkspaceUsageService(db).assert_run_access(
            workspace_id=principal.workspace_id,
            user_id=principal.user_id,
            run_id=agent_run_id,
        )
    except WorkspaceRunAccessDenied:
        raise HTTPException(status_code=404, detail="Agent run not found") from None

    services = get_agent_services(request)
    events = await services.event_store.list_by_agent_run_id(agent_run_id)

    return [event.model_dump(mode="json") for event in events]


@router.get("/runs/{agent_run_id}/stream")
async def stream_agent_events(
    request: Request,
    agent_run_id: str,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    _validate_agent_run_id(agent_run_id)

    try:
        await WorkspaceUsageService(db).assert_run_access(
            workspace_id=principal.workspace_id,
            user_id=principal.user_id,
            run_id=agent_run_id,
        )
    except WorkspaceRunAccessDenied:
        raise HTTPException(status_code=404, detail="Agent run not found") from None

    services = get_agent_services(request)

    async def event_generator():
        existing_events = await services.event_store.list_by_agent_run_id(agent_run_id)

        for event in existing_events:
            yield f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"

            if _is_terminal_stream_event(event):
                return

        async for event in services.event_stream.subscribe(agent_run_id):
            yield f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"

            if _is_terminal_stream_event(event):
                return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.post("/runs/{agent_run_id}/approve")
async def approve_agent_run(
    request: Request,
    agent_run_id: str,
    body: AgentApproveRequest,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _validate_agent_run_id(agent_run_id)

    services = get_agent_services(request)
    usage_service = WorkspaceUsageService(db)
    try:
        admission = await usage_service.resume_agent_run(
            workspace_id=principal.workspace_id,
            user_id=principal.user_id,
            run_id=agent_run_id,
        )
    except (WorkspaceRunAccessDenied, WorkspaceQuotaExceeded):
        raise HTTPException(status_code=404, detail="Agent run not found") from None
    state = await services.state_store.load(agent_run_id)

    if state is None:
        await usage_service.finish_agent_run(
            run_id=agent_run_id,
            status="failed",
            rejection_reason="state_missing",
        )
        raise HTTPException(status_code=404, detail="Agent run not found")

    state, recorder = await services.runner.resume_after_approval(
        state=state,
        approved=body.approved,
        rejection_reason=body.reason,
        tool_names=body.tools or None,
        context=AgentRuntimeContext(
            agent_run_id=agent_run_id,
            user_id=str(principal.user_id),
        ),
        usage_budget=UsageBudget(
            max_total_tokens=admission.max_total_tokens,
            max_llm_calls=admission.max_llm_calls,
            max_tool_calls=admission.max_tool_calls,
        ),
    )

    usage = state.meta.get("usage") or {}
    await usage_service.finish_agent_run(
        run_id=agent_run_id,
        status=str(state.status),
        usage=usage,
        tool_calls=int(usage.get("tool_calls") or 0),
    )

    return {
        "agent_run_id": state.agent_run_id,
        "status": state.status,
        "steps": state.steps,
        "final_output": state.final_output,
        "pending_approval": (
            state.pending_approval.model_dump() if state.pending_approval else None
        ),
        "errors": [error.model_dump() for error in state.errors],
        "events": [event.model_dump(mode="json") for event in recorder.events],
    }
