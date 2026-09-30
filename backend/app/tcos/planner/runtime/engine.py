from __future__ import annotations

from collections.abc import Callable

from app.tcos.compiler import compile_business_plan
from app.tcos.planner.product_planning import (
    ProductPlannerRegistry,
)
from app.tcos.planner.runtime.planner import Planner
from app.tcos.planner.runtime.advisory_telemetry import (
    PLANNER_ADVISORY_OBSERVED_EVENT,
    PlannerAdvisoryTelemetryProjector,
)
from app.tcos.planner.runtime.models import PlannerSession, PlanningStatus
from app.tcos.planner.runtime.planning_inputs import build_default_planning_context
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)
from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.verification import VerificationEngine
from app.tcos.planning_repair import RepairEngine
from app.tcos.planning_learning import LearningEngine
from app.tcos.planner.memory import PlanningMemory


class PlannerRuntime:
    def __init__(
        self,
        *,
        product_planners: ProductPlannerRegistry | None = None,
        is_semantic_capability: (Callable[[str], bool] | None) = None,
        runtime_node_for_capability: (
            Callable[[str], str | None] | None
        ) = None,
    ) -> None:
        self._product_planners = product_planners
        self._is_semantic_capability = is_semantic_capability
        self._runtime_node_for_capability = (
            runtime_node_for_capability
        )

    def plan_goal(
        self,
        *,
        goal: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
        planning_context: (PlanningContext | None) = None,
    ) -> PlannerSession:
        session = PlannerSession(
            goal=goal,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        if planning_context is None:
            planning_context = build_default_planning_context(
                user_message=goal,
            )
        else:
            planning_context = planning_context.model_copy(deep=True)

        session.context = planning_context.model_dump(mode="json")

        session.record(
            "PlanningStarted",
            goal=goal,
            planning_context=session.context,
        )

        session.status = PlanningStatus.PLANNING

        intent = detect_intent(text=goal)
        session.record(
            "IntentDetected",
            intent=intent.model_dump(mode="json"),
        )

        planner = Planner(
            product_planners=self._product_planners,
        )

        try:
            generation_result = planner.plan_result(
                intent=intent,
                context=planning_context,
            )
        except ValueError as exc:
            session.status = PlanningStatus.FAILED
            session.record(
                "PlanningFailed",
                reason=str(exc),
                intent=intent.model_dump(mode="json"),
            )
            session.metrics = {
                "event_count": len(session.events),
                "compiled": False,
                "failure_reason": str(exc),
            }
            return session

        if generation_result.requires_clarification:
            product_result = generation_result.product_result

            if product_result is None or product_result.clarification is None:
                raise RuntimeError("clarification result missing clarification payload")

            clarification = product_result.clarification

            session.clarification = clarification.model_dump(mode="json")

            session.status = PlanningStatus.CLARIFICATION_REQUIRED

            session.record(
                "PlanningClarificationRequired",
                product_id=product_result.product_id,
                **session.clarification,
            )

            session.metrics = {
                "event_count": len(session.events),
                "compiled": False,
                "clarification_required": True,
                "clarification_reason_code": (clarification.reason_code),
                "clarification_missing_fields": list(clarification.missing_fields),
                "product_id": (product_result.product_id),
            }

            return session

        selected_candidate = generation_result.candidates[0]

        session.selected_candidate = selected_candidate.model_dump(mode="json")

        advisory_telemetry = PlannerAdvisoryTelemetryProjector().project(
            candidate=selected_candidate,
        )

        session.record(
            PLANNER_ADVISORY_OBSERVED_EVENT,
            candidate_id=selected_candidate.id,
            **advisory_telemetry.model_dump(mode="json"),
        )

        verifier = VerificationEngine()

        if (
            self._is_semantic_capability is None
            and self._runtime_node_for_capability is None
        ):
            # Keep the historical call contract for compatibility,
            # including tests/adapters that replace VerificationEngine
            # with a minimal verify(candidate) implementation.
            verification = verifier.verify(
                selected_candidate
            )
        else:
            verification = verifier.verify(
                selected_candidate,
                is_semantic_capability=(
                    self._is_semantic_capability
                ),
                runtime_node_for_capability=(
                    self._runtime_node_for_capability
                ),
            )
        session.verification_result = verification.model_dump(mode="json")
        session.record(
            "VerificationCompleted",
            passed=verification.passed,
            confidence=verification.confidence,
            issue_count=len(verification.issues),
        )

        if not verification.passed:
            PlanningMemory().record_failure(
                intent_name=intent.name,
                candidate=selected_candidate,
            )
            session.record(
                "PlanningMemoryRecorded",
                outcome="failure",
                candidate_id=selected_candidate.id,
                intent_name=intent.name,
            )

            repair = RepairEngine().plan_repair(verification)
            session.repair_result = repair.model_dump(mode="json")
            repair_actions = repair.plan.actions if repair.plan else []
            repair_action_types = [
                action.get("type")
                for action in repair_actions
                if isinstance(action, dict)
            ]
            repair_artifact_ids = [
                action.get("artifact_id")
                for action in repair_actions
                if isinstance(action, dict) and action.get("artifact_id")
            ]

            session.record(
                "RepairPlanned",
                repairable=repair.repairable,
                strategy=repair.plan.strategy if repair.plan else None,
                confidence=repair.plan.confidence if repair.plan else None,
                action_count=len(repair_actions),
                action_types=repair_action_types,
                artifact_ids=repair_artifact_ids,
            )
            session.status = PlanningStatus.FAILED
            session.metrics = {
                "event_count": len(session.events),
                "compiled": False,
                "verified": False,
                "repairable": repair.repairable,
                "verification_issue_count": len(verification.issues),
                "repair_action_count": len(repair_actions),
                "repair_action_types": repair_action_types,
                "repair_artifact_ids": repair_artifact_ids,
                "planning_memory_outcome": "failure",
                "planning_memory_candidate_id": selected_candidate.id,
                **advisory_telemetry.metric_fields(),
            }
            return session

        business_plan = selected_candidate.business_plan

        session.business_plan = business_plan
        session.record(
            "BusinessPlanCreated",
            business_plan_id=business_plan.id,
            task_count=len(business_plan.tasks),
        )

        compilation = compile_business_plan(
            business_plan,
            is_semantic_capability=(
                self._is_semantic_capability
            ),
            runtime_node_for_capability=(
                self._runtime_node_for_capability
            ),
        )
        session.compilation = compilation

        if compilation.ok:
            session.status = PlanningStatus.COMPILED
            session.record(
                "CompilationSucceeded",
                execution_graph_id=compilation.execution_graph.id
                if compilation.execution_graph
                else None,
            )
        else:
            session.status = PlanningStatus.FAILED
            session.record(
                "CompilationFailed",
                diagnostics=[
                    diagnostic.model_dump(mode="json")
                    for diagnostic in compilation.diagnostics
                ],
            )

        if compilation.ok:
            PlanningMemory().record_success(
                intent_name=intent.name,
                candidate=selected_candidate,
                latency_ms=business_plan.metadata.estimated_latency_ms,
                cost=business_plan.metadata.estimated_cost,
            )
            session.record(
                "PlanningMemoryRecorded",
                outcome="success",
                candidate_id=selected_candidate.id,
                intent_name=intent.name,
            )

        learning_engine = LearningEngine()
        learning_episode = learning_engine.build_episode(
            planner_session_id=session.session_id,
            goal=session.goal,
            selected_candidate=session.selected_candidate,
            business_plan=(
                session.business_plan.model_dump(mode="json")
                if session.business_plan
                else None
            ),
            compilation=(
                session.compilation.model_dump(mode="json")
                if session.compilation
                else None
            ),
            verification_result=session.verification_result,
            repair_result=session.repair_result,
            metrics=session.metrics,
        )
        learning_result = learning_engine.analyze(learning_episode)

        session.learning_episode = learning_result.episode.model_dump(mode="json")

        session.record(
            "LearningCompleted",
            insight_count=len(learning_result.insights),
            episode_id=learning_result.episode.id,
        )

        session.metrics = {
            "event_count": len(session.events),
            "task_count": len(business_plan.tasks),
            "compiled": compilation.ok,
            "learning_insight_count": len(learning_result.insights),
            "planning_memory_outcome": "success" if compilation.ok else None,
            "planning_memory_candidate_id": selected_candidate.id
            if compilation.ok
            else None,
            **advisory_telemetry.metric_fields(),
        }

        return session

    def plan_customer_reply(
        self,
        *,
        goal: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
        planning_context: PlanningContext | None = None,
    ) -> PlannerSession:
        """
        Backward-compatible alias for plan_goal().

        Product-aware callers should inject Product planners and use
        plan_goal(). Core planning itself is product-neutral.
        """

        return self.plan_goal(
            goal=goal,
            user_id=user_id,
            tenant_id=tenant_id,
            planning_context=planning_context,
        )
