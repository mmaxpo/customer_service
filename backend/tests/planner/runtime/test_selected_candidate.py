from app.tcos.planner.runtime import PlannerRuntime


def test_selected_candidate_saved_in_session():

    runtime = PlannerRuntime()

    session = runtime.plan_goal(goal="Summarize https://example.com")

    assert session.selected_candidate is not None
    assert session.selected_candidate["source"] == "capability_reasoner"
    assert session.selected_candidate["score"] > 0
