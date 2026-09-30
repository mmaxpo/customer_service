from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class QueueWorkloadItem(BaseModel):
    queue_id: UUID
    queue_name: str
    team_id: UUID | None = None
    channel: str | None = None
    intent: str | None = None
    priority: str | None = None
    open_or_pending_tickets: int


class TeamWorkloadItem(BaseModel):
    team_id: UUID
    team_name: str
    open_or_pending_tickets: int
    member_count: int


class AgentWorkloadItem(BaseModel):
    assigned_to: str
    open_or_pending_tickets: int


class WorkloadReport(BaseModel):
    queues: list[QueueWorkloadItem]
    teams: list[TeamWorkloadItem]
    agents: list[AgentWorkloadItem]
