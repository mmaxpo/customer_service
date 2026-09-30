from __future__ import annotations

from app.workflow_operations.quality.schemas import (
    WorkflowDeploymentGateRequest,
    WorkflowDeploymentGateResult,
    WorkflowQualityInput,
    WorkflowQualityScore,
)


class WorkflowQualityService:
    def score(self, payload: WorkflowQualityInput) -> WorkflowQualityScore:
        reasons: list[str] = []
        components: dict = {}

        evaluation_score = 1.0
        if payload.evaluation is not None:
            evaluation_score = float(payload.evaluation.score)
            components["evaluation_score"] = evaluation_score

            if not payload.evaluation.passed:
                reasons.append("evaluation_failed")

        regression_score = 1.0
        if payload.regression is not None:
            if payload.regression.regression_detected:
                regression_score = 0.0
                reasons.append("regression_detected")
            elif payload.regression.improved:
                regression_score = 1.0
            components["regression_score"] = regression_score
            components["score_delta"] = payload.regression.score_delta

        metrics_score = self._score_metrics(payload.metrics_summary)
        components["metrics_score"] = metrics_score

        score = round(
            (evaluation_score * 0.55 + regression_score * 0.30 + metrics_score * 0.15),
            4,
        )

        grade = self._grade(score)
        passed = score >= 0.8 and "regression_detected" not in reasons

        return WorkflowQualityScore(
            score=score,
            grade=grade,
            passed=passed,
            reasons=reasons,
            components=components,
        )

    def deployment_gate(
        self,
        request: WorkflowDeploymentGateRequest,
    ) -> WorkflowDeploymentGateResult:
        score = self.score(request.quality)
        blocked_reasons: list[str] = []

        if (
            request.quality.evaluation is None
            and request.quality.regression is None
            and not request.quality.metrics_summary
        ):
            blocked_reasons.append("quality_evidence_missing")

        if score.score < request.min_score:
            blocked_reasons.append(
                f"score_below_minimum:{score.score}<{request.min_score}"
            )

        if (
            request.block_on_regression
            and request.quality.regression is not None
            and request.quality.regression.regression_detected
        ):
            blocked_reasons.append("regression_detected")

        allowed = not blocked_reasons

        return WorkflowDeploymentGateResult(
            allowed=allowed,
            score=score,
            min_score=request.min_score,
            block_on_regression=request.block_on_regression,
            blocked_reasons=blocked_reasons,
        )

    def _score_metrics(self, metrics: dict) -> float:
        if not metrics:
            return 1.0

        run_count = int(metrics.get("run_count") or 0)
        success_rate = float(metrics.get("success_rate") or 0.0)
        total_errors = int(metrics.get("total_errors") or 0)

        if run_count == 0:
            return 1.0

        score = success_rate

        if total_errors > 0:
            score -= min(0.25, total_errors * 0.05)

        return max(0.0, min(1.0, round(score, 4)))

    def _grade(self, score: float) -> str:
        if score >= 0.95:
            return "A"
        if score >= 0.85:
            return "B"
        if score >= 0.75:
            return "C"
        if score >= 0.60:
            return "D"
        return "F"
