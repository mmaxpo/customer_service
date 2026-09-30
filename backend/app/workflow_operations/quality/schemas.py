from __future__ import annotations

from pydantic import BaseModel, Field

from app.workflow_operations.evaluations.regression import WorkflowRegressionCheckResult
from app.workflow_operations.evaluations.schemas import WorkflowEvaluationResult


class WorkflowQualityInput(BaseModel):
    evaluation: WorkflowEvaluationResult | None = None
    regression: WorkflowRegressionCheckResult | None = None
    metrics_summary: dict = Field(default_factory=dict)


class WorkflowQualityScore(BaseModel):
    score: float
    grade: str
    passed: bool
    reasons: list[str] = Field(default_factory=list)
    components: dict = Field(default_factory=dict)


class WorkflowDeploymentGateRequest(BaseModel):
    quality: WorkflowQualityInput
    min_score: float = 0.8
    block_on_regression: bool = True


class WorkflowDeploymentGateResult(BaseModel):
    allowed: bool
    score: WorkflowQualityScore
    min_score: float
    block_on_regression: bool
    blocked_reasons: list[str] = Field(default_factory=list)
