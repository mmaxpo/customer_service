from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExecutionEdgeType(StrEnum):
    DEFAULT = "default"
    CONDITIONAL = "conditional"
    ERROR = "error"


class ExecutionNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    node_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    inputs: list[dict[str, Any]] = Field(default_factory=list)
    outputs: list[dict[str, Any]] = Field(default_factory=list)
    retry_policy: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    target: str
    edge_type: ExecutionEdgeType = ExecutionEdgeType.DEFAULT
    condition: str | None = None
    mapping: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionGraphMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compiler_version: str = "0.1"
    source_business_plan_id: str | None = None
    estimated_cost: float | None = Field(default=None, ge=0)
    estimated_latency_ms: int | None = Field(default=None, ge=0)
    extra: dict[str, Any] = Field(default_factory=dict)


class ExecutionGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nodes: list[ExecutionNode]
    edges: list[ExecutionEdge] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    metadata: ExecutionGraphMetadata = Field(default_factory=ExecutionGraphMetadata)
    schema_version: str = "execution_ir.v1"
