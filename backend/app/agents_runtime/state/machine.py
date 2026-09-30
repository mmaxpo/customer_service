from __future__ import annotations

from enum import StrEnum


class AgentStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ALLOWED_TRANSITIONS: dict[AgentStatus, set[AgentStatus]] = {
    AgentStatus.CREATED: {AgentStatus.RUNNING, AgentStatus.FAILED},
    AgentStatus.RUNNING: {
        AgentStatus.PAUSED,
        AgentStatus.COMPLETED,
        AgentStatus.FAILED,
        AgentStatus.CANCELLED,
    },
    AgentStatus.PAUSED: {
        AgentStatus.RUNNING,
        AgentStatus.FAILED,
        AgentStatus.CANCELLED,
    },
    AgentStatus.COMPLETED: set(),
    AgentStatus.FAILED: set(),
    AgentStatus.CANCELLED: set(),
}


class InvalidAgentStateTransition(Exception):
    pass


def transition_status(current: AgentStatus, target: AgentStatus) -> AgentStatus:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidAgentStateTransition(
            f"Cannot transition from {current} to {target}"
        )

    return target
