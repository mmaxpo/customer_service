from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentRuntimeContext(BaseModel):
    agent_run_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str | None = None
    workflow_run_id: str | None = None
    thread_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
