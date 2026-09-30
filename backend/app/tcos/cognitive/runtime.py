from __future__ import annotations

from collections.abc import Callable

from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContextLoader,
    ObjectiveCognitiveReference,
)
from app.tcos.cognitive.models import CognitiveSession, CognitiveSessionStatus
from app.tcos.cognitive.objective_lifecycle_telemetry import (
    OBJECTIVE_LIFECYCLE_TELEMETRY_EVENT,
    OBJECTIVE_LIFECYCLE_TELEMETRY_METRIC_KEY,
    ObjectiveLifecycleTelemetryProjector,
)
from app.tcos.cognitive.objective_repair_delegation import (
    OBJECTIVE_REPAIR_DELEGATION_EVENT,
    OBJECTIVE_REPAIR_DELEGATION_METRIC_KEY,
    ObjectiveRepairDelegationDecision,
    ObjectiveRepairDelegationReasoner,
)
from app.tcos.compiler.execution_ir.models import ExecutionGraph
from app.tcos.execution import ExecutionCoordinator
from app.tcos.planner.runtime import (
    PlannerRuntime,
    PlanningStatus,
)
from app.tcos.planner.product_planning import (
    ProductPlannerRegistry,
)
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)
from app.tcos.planner.runtime.planning_inputs import (
    build_default_planning_context,
)


class CognitiveRuntime:
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

    def execute_goal(
        self,
        *,
        goal: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
        planning_context: PlanningContext | None = None,
    ) -> CognitiveSession:
        session = CognitiveSession(goal=goal)
        session.record("CognitiveSessionCreated", goal=goal)

        planner_session = PlannerRuntime(
            product_planners=self._product_planners,
            is_semantic_capability=(
                self._is_semantic_capability
            ),
            runtime_node_for_capability=(
                self._runtime_node_for_capability
            ),
        ).plan_goal(
            goal=goal,
            user_id=user_id,
            tenant_id=tenant_id,
            planning_context=planning_context,
        )

        session.planner_session = planner_session.model_dump(mode="json")
        session.record(
            "PlannerCompleted",
            planner_session_id=planner_session.session_id,
            planner_status=planner_session.status,
        )

        if planner_session.status == PlanningStatus.CLARIFICATION_REQUIRED:
            session.status = CognitiveSessionStatus.COMPLETED
            session.record(
                "CognitiveClarificationRequired",
                clarification=(planner_session.clarification),
            )
            session.record("CognitiveSessionCompleted")

        elif planner_session.status == PlanningStatus.COMPILED:
            execution_graph_data = (
                planner_session.compilation.execution_graph.model_dump(mode="json")
                if planner_session.compilation
                and planner_session.compilation.execution_graph
                else None
            )

            if execution_graph_data:
                execution_graph = ExecutionGraph.model_validate(execution_graph_data)
                execution_session = ExecutionCoordinator().prepare(execution_graph)
                session.execution_session = execution_session.model_dump(mode="json")
                session.record(
                    "ExecutionPrepared",
                    execution_id=execution_session.execution_id,
                    node_count=execution_session.metrics.get("node_count"),
                    edge_count=execution_session.metrics.get("edge_count"),
                )

            session.status = CognitiveSessionStatus.COMPLETED
            session.record("CognitiveSessionCompleted")
        else:
            session.status = CognitiveSessionStatus.FAILED
            session.record("CognitiveSessionFailed")

        session.metrics = {
            "planner_status": planner_session.status,
            "planner_event_count": len(planner_session.events),
            "execution_prepared": session.execution_session is not None,
            "cognitive_event_count": len(session.events),
        }

        return session

    async def execute_goal_runtime(
        self,
        *,
        goal: str,
        ctx,
        user_id: str | None = None,
        tenant_id: str | None = None,
        strict: bool = True,
        objective: (ObjectiveCognitiveReference | None) = None,
    ):
        """
        Full cognitive execution.

        Goal
            ↓
        Planner
            ↓
        Compiler
            ↓
        ExecutionCoordinator
            ↓
        Workflow Runtime
        """

        planning_context = None
        objective_context = None

        if objective is not None:
            db = getattr(ctx, "db", None)

            if db is None:
                raise ValueError(
                    "Objective cognitive context requires a runtime database session"
                )

            scoped_user_id = user_id or getattr(ctx, "user_id", None)

            if scoped_user_id is None:
                raise ValueError(
                    "Objective cognitive context requires an authenticated user id"
                )

            scoped_tenant_id = (
                tenant_id if tenant_id is not None else getattr(ctx, "tenant_id", None)
            )

            objective_context = await ObjectiveCognitiveContextLoader(
                db
            ).load_for_objective(
                user_id=scoped_user_id,
                objective_namespace=(objective.namespace),
                objective_ref=(objective.objective_ref),
                tenant_id=(
                    str(scoped_tenant_id) if scoped_tenant_id is not None else None
                ),
            )

            planning_context = build_default_planning_context(
                user_message=goal,
                objective_context=(objective_context),
            )

        session = self.execute_goal(
            goal=goal,
            user_id=user_id,
            tenant_id=tenant_id,
            planning_context=planning_context,
        )

        if objective is not None:
            delegation = self._project_objective_repair_delegation(
                session=session,
                objective_context=objective_context,
            )

            self._project_objective_lifecycle_telemetry(
                session=session,
                objective_context=objective_context,
                delegation=delegation,
            )

        if session.execution_session is None:
            return session

        from app.tcos.compiler.execution_ir.models import ExecutionGraph
        from app.tcos.execution import ExecutionCoordinator

        execution_graph_data = session.execution_session.get("execution_graph")

        graph = ExecutionGraph.model_validate(execution_graph_data)

        execution = await ExecutionCoordinator().execute(
            graph,
            ctx=ctx,
            message=goal,
            strict=strict,
        )

        session.execution_session = execution.model_dump(mode="json")

        session.record(
            "RuntimeExecutionFinished",
            runtime_status=execution.metrics.get("runtime_status"),
        )

        session.metrics["runtime_executed"] = True
        session.metrics["cognitive_event_count"] = len(session.events)

        return session

    @staticmethod
    def _project_objective_repair_delegation(
        *,
        session: CognitiveSession,
        objective_context,
    ) -> ObjectiveRepairDelegationDecision:
        decision = ObjectiveRepairDelegationReasoner().reason(objective_context)

        session.metrics[OBJECTIVE_REPAIR_DELEGATION_METRIC_KEY] = decision.model_dump(
            mode="json"
        )

        session.record(
            OBJECTIVE_REPAIR_DELEGATION_EVENT,
            kind=decision.kind,
            requested=decision.requested,
            reason_code=decision.reason_code,
            resolution_record_id=(
                str(decision.resolution_record_id)
                if decision.resolution_record_id is not None
                else None
            ),
            repair_execution_id=(
                str(decision.repair_execution_id)
                if decision.repair_execution_id is not None
                else None
            ),
            requested_attempt_number=(decision.requested_attempt_number),
        )

        session.metrics["cognitive_event_count"] = len(session.events)

        return decision

    @staticmethod
    def _project_objective_lifecycle_telemetry(
        *,
        session: CognitiveSession,
        objective_context,
        delegation: ObjectiveRepairDelegationDecision,
    ) -> None:
        telemetry = ObjectiveLifecycleTelemetryProjector().project(
            objective_context=objective_context,
            planner_session=session.planner_session,
            delegation=delegation,
        )

        payload = telemetry.model_dump(mode="json")

        session.metrics[OBJECTIVE_LIFECYCLE_TELEMETRY_METRIC_KEY] = payload

        session.record(
            OBJECTIVE_LIFECYCLE_TELEMETRY_EVENT,
            **payload,
        )

        session.metrics["cognitive_event_count"] = len(session.events)
