from __future__ import annotations

from app.tcos.planning_repair.models import RepairPlan, RepairResult, RepairStrategyType
from app.tcos.verification.models import VerificationResult, VerificationSeverity


class RepairEngine:
    def plan_repair(self, verification: VerificationResult) -> RepairResult:
        if verification.passed:
            return RepairResult(repairable=False, issues=[])

        error_codes = [
            issue.code
            for issue in verification.issues
            if issue.severity == VerificationSeverity.ERROR
        ]

        if "missing_capability" in error_codes:
            return RepairResult(
                repairable=True,
                plan=RepairPlan(
                    strategy=RepairStrategyType.REPLAN,
                    reason="Plan references unavailable capabilities.",
                    confidence=0.8,
                    actions=[
                        {
                            "type": "replan",
                            "reason": "missing_capability",
                        }
                    ],
                ),
                issues=[issue.model_dump(mode="json") for issue in verification.issues],
            )

        if "missing_artifact_producer" in error_codes:
            artifact_ids = [
                issue.details.get("artifact_id")
                for issue in verification.issues
                if issue.code == "missing_artifact_producer"
                and isinstance(issue.details, dict)
                and issue.details.get("artifact_id")
            ]

            actions = [
                {
                    "type": "insert_missing_artifact_producer",
                    "artifact_id": artifact_id,
                    "reason": "missing_artifact_producer",
                }
                for artifact_id in artifact_ids
            ] or [
                {
                    "type": "replan",
                    "reason": "missing_artifact_producer",
                }
            ]

            return RepairResult(
                repairable=True,
                plan=RepairPlan(
                    strategy=RepairStrategyType.REPLAN,
                    reason="Plan consumes an artifact that is not produced by any earlier operation.",
                    confidence=0.85,
                    actions=actions,
                ),
                issues=[issue.model_dump(mode="json") for issue in verification.issues],
            )

        if "no_tasks" in error_codes:
            return RepairResult(
                repairable=True,
                plan=RepairPlan(
                    strategy=RepairStrategyType.REPLAN,
                    reason="Business plan contains no tasks.",
                    confidence=0.9,
                    actions=[
                        {
                            "type": "replan",
                            "reason": "empty_business_plan",
                        }
                    ],
                ),
                issues=[issue.model_dump(mode="json") for issue in verification.issues],
            )

        return RepairResult(
            repairable=True,
            plan=RepairPlan(
                strategy=RepairStrategyType.ESCALATE,
                reason="Failure requires human review.",
                confidence=0.5,
                actions=[
                    {
                        "type": "escalate",
                    }
                ],
            ),
            issues=[issue.model_dump(mode="json") for issue in verification.issues],
        )
