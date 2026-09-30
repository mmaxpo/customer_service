from app.tcos.planner.runtime import PlannerRuntime


def test_runtime_session_can_be_serialized_for_api():
    runtime = PlannerRuntime()

    session = runtime.plan_goal(
        goal="Summarize https://example.com",
    )

    payload = {
        "session_id": session.session_id,
        "status": session.status,
        "business_plan": session.business_plan.model_dump(mode="json"),
        "compilation": session.compilation.model_dump(mode="json"),
        "metrics": session.metrics,
        "events": [e.model_dump(mode="json") for e in session.events],
    }

    assert payload["status"] == "compiled"
    assert payload["business_plan"]["tasks"]
    assert payload["compilation"]["ok"] is True
