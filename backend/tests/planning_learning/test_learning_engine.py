from app.tcos.planning_learning import LearningEngine, LearningEpisodeStatus
from app.tcos.planner.runtime import PlannerRuntime


def test_learning_engine_builds_episode_from_planner_session():
    session = PlannerRuntime().plan_goal(goal="Summarize https://example.com")

    episode = LearningEngine().build_episode(
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

    assert episode.planner_session_id == session.session_id
    assert episode.goal == "Summarize https://example.com"
    assert episode.selected_candidate is not None
    assert episode.business_plan is not None
    assert episode.compilation is not None
    assert episode.verification_result is not None
    assert episode.metrics["compiled"] is True


def test_learning_engine_analyzes_verified_episode():
    session = PlannerRuntime().plan_goal(goal="Summarize https://example.com")
    engine = LearningEngine()
    episode = engine.build_episode(
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

    result = engine.analyze(episode)

    assert result.episode.status == LearningEpisodeStatus.ANALYZED
    assert any(insight.code == "verified_plan" for insight in result.insights)
