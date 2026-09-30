from __future__ import annotations

from pydantic import BaseModel, Field

from app.workflow_operations.evaluations.schemas import (
    WorkflowEvaluationResult,
)


class WorkflowRegressionCheckRequest(BaseModel):
    baseline: WorkflowEvaluationResult
    candidate: WorkflowEvaluationResult
    min_score_delta: float = 0.0


class WorkflowRegressionCaseDiff(BaseModel):
    name: str
    baseline_passed: bool | None = None
    candidate_passed: bool | None = None
    regressed: bool = False
    improved: bool = False
    baseline_score: float | None = None
    candidate_score: float | None = None


class WorkflowRegressionCheckResult(BaseModel):
    regression_detected: bool
    improved: bool
    baseline_score: float
    candidate_score: float
    score_delta: float
    min_score_delta: float
    regressed_cases: list[WorkflowRegressionCaseDiff] = Field(default_factory=list)
    improved_cases: list[WorkflowRegressionCaseDiff] = Field(default_factory=list)
    unchanged_cases: list[WorkflowRegressionCaseDiff] = Field(default_factory=list)


class WorkflowRegressionDetector:
    def check(
        self,
        *,
        baseline: WorkflowEvaluationResult,
        candidate: WorkflowEvaluationResult,
        min_score_delta: float = 0.0,
    ) -> WorkflowRegressionCheckResult:
        baseline_by_name = {case.name: case for case in baseline.cases}
        candidate_by_name = {case.name: case for case in candidate.cases}

        names = sorted(set(baseline_by_name) | set(candidate_by_name))

        regressed_cases = []
        improved_cases = []
        unchanged_cases = []

        for name in names:
            base = baseline_by_name.get(name)
            cand = candidate_by_name.get(name)

            base_passed = base.passed if base else None
            cand_passed = cand.passed if cand else None

            base_score = base.score if base else None
            cand_score = cand.score if cand else None

            regressed = bool(base_passed is True and cand_passed is not True)
            improved = bool(base_passed is not True and cand_passed is True)

            item = WorkflowRegressionCaseDiff(
                name=name,
                baseline_passed=base_passed,
                candidate_passed=cand_passed,
                regressed=regressed,
                improved=improved,
                baseline_score=base_score,
                candidate_score=cand_score,
            )

            if regressed:
                regressed_cases.append(item)
            elif improved:
                improved_cases.append(item)
            else:
                unchanged_cases.append(item)

        score_delta = candidate.score - baseline.score

        regression_detected = bool(
            regressed_cases or score_delta < -abs(min_score_delta)
        )

        improved = bool(improved_cases or score_delta > abs(min_score_delta))

        return WorkflowRegressionCheckResult(
            regression_detected=regression_detected,
            improved=improved,
            baseline_score=baseline.score,
            candidate_score=candidate.score,
            score_delta=score_delta,
            min_score_delta=min_score_delta,
            regressed_cases=regressed_cases,
            improved_cases=improved_cases,
            unchanged_cases=unchanged_cases,
        )
