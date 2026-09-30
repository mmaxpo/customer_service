from app.tcos.planner.runtime import PlannerRuntime, PlanningStatus


def test_planner_runtime_creates_compiled_customer_reply_session():
    runtime = PlannerRuntime()

    session = runtime.plan_goal(goal="Summarize https://example.com")

    assert session.status == PlanningStatus.COMPILED
    assert session.business_plan is not None
    assert session.compilation is not None
    assert session.compilation.ok is True
    assert session.compilation.execution_graph is not None
    assert session.metrics["compiled"] is True


def test_planner_runtime_records_events():
    runtime = PlannerRuntime()

    session = runtime.plan_goal(goal="Summarize https://example.com")

    event_types = [event.type for event in session.events]

    assert event_types == [
        "PlanningStarted",
        "IntentDetected",
        "planner.advisory_context_observed",
        "VerificationCompleted",
        "BusinessPlanCreated",
        "CompilationSucceeded",
        "PlanningMemoryRecorded",
        "LearningCompleted",
    ]
