from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from app.runtime.objectives.cognition import (
    ObjectiveCognitiveReference,
)
import uuid
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from app.core.session import get_db as get_session
from app.api.auth import get_current_user
from app.api.workflows import get_event_sink, get_run_store
from app.runtime_services import build_application_runtime_context
from app.cognitive_runtime import (
    build_application_cognitive_runtime,
)
from app.tcos.cognitive import (
    compiled_runtime_workflow_from_session,
)
# ============================================================
# HTTP transport schemas
# ============================================================


class ExecuteGoalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str


class ExecuteGoalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: dict


class ExecuteGoalRuntimeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str
    thread_id: str | None = None
    strict: bool = True

    objective: ObjectiveCognitiveReference | None = None


class ExecuteGoalRuntimeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: dict


# ============================================================
# TCOS HTTP API
# ============================================================

router = APIRouter(
    prefix="/tcos",
    tags=["TCOS"],
)


@router.post(
    "/execute-goal",
    response_model=ExecuteGoalResponse,
)
async def execute_goal(
    payload: ExecuteGoalRequest,
    current_user=Depends(get_current_user),
):
    session = build_application_cognitive_runtime().execute_goal(
        goal=payload.goal,
        user_id=str(current_user.id),
    )

    data = session.model_dump(mode="json")
    data["compiled_runtime_workflow"] = compiled_runtime_workflow_from_session(session)

    return ExecuteGoalResponse(
        session=data,
    )


@router.post(
    "/execute-goal-runtime",
    response_model=ExecuteGoalRuntimeResponse,
)
async def execute_goal_runtime(
    payload: ExecuteGoalRuntimeRequest,
    request: Request,
    db=Depends(get_session),
    current_user=Depends(get_current_user),
    run_store=Depends(get_run_store),
    event_sink=Depends(get_event_sink),
):
    thread_id = payload.thread_id or str(uuid.uuid4())

    ctx = build_application_runtime_context(
        request=request,
        user_id=UUID(str(current_user.id)),
        thread_id=UUID(thread_id),
        db=db,
        extras={},
        run_store=run_store,
        event_sink=event_sink,
    )

    session = await build_application_cognitive_runtime(
        is_semantic_capability=(ctx.services.capability_registry.has_capability),
    ).execute_goal_runtime(
        goal=payload.goal,
        ctx=ctx,
        user_id=str(current_user.id),
        strict=payload.strict,
        objective=payload.objective,
    )

    return ExecuteGoalRuntimeResponse(
        session=session.model_dump(mode="json"),
    )


__all__ = ["router"]
