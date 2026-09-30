from __future__ import annotations

from app.tcos.planning_learning.models import (
    LearningEpisode,
    LearningEpisodeStatus,
    LearningInsight,
    LearningResult,
)


class LearningEngine:
    def build_episode(
        self,
        *,
        planner_session_id: str,
        goal: str,
        selected_candidate: dict | None = None,
        business_plan: dict | None = None,
        compilation: dict | None = None,
        verification_result: dict | None = None,
        repair_result: dict | None = None,
        metrics: dict | None = None,
    ) -> LearningEpisode:
        return LearningEpisode(
            planner_session_id=planner_session_id,
            goal=goal,
            selected_candidate=selected_candidate,
            business_plan=business_plan,
            compilation=compilation,
            verification_result=verification_result,
            repair_result=repair_result,
            metrics=metrics or {},
        )

    def analyze(self, episode: LearningEpisode) -> LearningResult:
        insights: list[LearningInsight] = []

        if episode.verification_result and episode.verification_result.get("passed"):
            insights.append(
                LearningInsight(
                    code="verified_plan",
                    message="Planner selected a candidate that passed verification.",
                    confidence=1.0,
                    evidence={"planner_session_id": episode.planner_session_id},
                )
            )

        memory_outcome = episode.metrics.get("planning_memory_outcome")
        memory_candidate_id = episode.metrics.get("planning_memory_candidate_id")

        if memory_outcome:
            insights.append(
                LearningInsight(
                    code=f"planning_memory:{memory_outcome}",
                    message=f"Planning memory recorded `{memory_outcome}` for selected candidate.",
                    confidence=0.9,
                    evidence={
                        "candidate_id": memory_candidate_id,
                        "outcome": memory_outcome,
                    },
                )
            )

        if episode.repair_result:
            insights.append(
                LearningInsight(
                    code="repair_required",
                    message="Planner session required repair recommendation.",
                    confidence=0.9,
                    evidence={"repair_result": episode.repair_result},
                )
            )

            plan = episode.repair_result.get("plan") or {}
            actions = plan.get("actions") or []

            for action in actions:
                action_type = action.get("type")

                insights.append(
                    LearningInsight(
                        code=f"repair_pattern:{action_type}",
                        message=f"Observed repair pattern `{action_type}`.",
                        confidence=0.95,
                        evidence=action,
                    )
                )

                artifact = action.get("artifact_id")
                if artifact:
                    insights.append(
                        LearningInsight(
                            code="missing_artifact_pattern",
                            message=f"Planner attempted to consume artifact `{artifact}` before it existed.",
                            confidence=0.95,
                            evidence={
                                "artifact_id": artifact,
                                "action": action_type,
                            },
                        )
                    )

        episode.status = LearningEpisodeStatus.ANALYZED

        return LearningResult(
            episode=episode,
            insights=insights,
        )
