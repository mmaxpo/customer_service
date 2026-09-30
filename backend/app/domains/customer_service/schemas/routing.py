from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class AutoAssignRequest(BaseModel):
    candidate_assignee_ids: list[UUID] = Field(..., min_length=1)
    strategy: str = Field(
        default="least_loaded", pattern="^(least_loaded|first_available)$"
    )
    reason: str | None = None


class AutoAssignDecision(BaseModel):
    ticket_id: UUID
    assigned_to: UUID
    strategy: str
    reason: str
    candidate_loads: dict[str, int]


class AutoAssignResult(BaseModel):
    decision: AutoAssignDecision
    assignment_id: UUID
