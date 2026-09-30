from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolRiskLevel(StrEnum):
    SAFE = "safe"
    SENSITIVE = "sensitive"
    DANGEROUS = "dangerous"


class AgentTool(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable[..., Any] = Field(exclude=True)
    risk_level: ToolRiskLevel = ToolRiskLevel.SAFE
    requires_approval: bool = False
