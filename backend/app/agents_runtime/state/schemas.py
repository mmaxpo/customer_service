from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.agents_runtime.state.machine import AgentStatus, transition_status


class AgentError(BaseModel):
    step: int
    message: str


class PendingApproval(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    call_id: str | None = None


class AgentState(BaseModel):
    agent_run_id: str = Field(default_factory=lambda: str(uuid4()))
    status: AgentStatus = AgentStatus.CREATED

    input_items: list[Any] = Field(default_factory=list)
    steps: int = 0
    final_output: str | None = None

    errors: list[AgentError] = Field(default_factory=list)
    pending_approval: PendingApproval | None = None

    vars: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)

    def transition_to(self, target: AgentStatus) -> None:
        self.status = transition_status(self.status, target)

    def mark_running(self) -> None:
        self.transition_to(AgentStatus.RUNNING)

    def mark_paused(self, approval: PendingApproval) -> None:
        self.transition_to(AgentStatus.PAUSED)
        self.pending_approval = approval

    def mark_completed(self, output: str) -> None:
        self.transition_to(AgentStatus.COMPLETED)
        self.final_output = output

    def mark_failed(self, error: str) -> None:
        if self.status not in {
            AgentStatus.FAILED,
            AgentStatus.COMPLETED,
            AgentStatus.CANCELLED,
        }:
            self.transition_to(AgentStatus.FAILED)

        self.errors.append(
            AgentError(
                step=self.steps,
                message=error,
            )
        )

    def resume_from_pause(self) -> None:
        if self.status != AgentStatus.PAUSED:
            raise ValueError("Can only resume from paused state.")

        self.pending_approval = None
        self.transition_to(AgentStatus.RUNNING)
