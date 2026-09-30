from app.tcos.planning_learning import LearningEngine
from app.tcos.planning_learning.models import LearningEpisode


def test_learning_engine_emits_memory_success_insight():
    episode = LearningEpisode(
        planner_session_id="planner",
        goal="Reply",
        metrics={
            "planning_memory_outcome": "success",
            "planning_memory_candidate_id": "template_customer_reply",
        },
    )

    result = LearningEngine().analyze(episode)

    insight = next(i for i in result.insights if i.code == "planning_memory:success")

    assert insight.evidence["candidate_id"] == "template_customer_reply"
    assert insight.evidence["outcome"] == "success"


def test_learning_engine_emits_memory_failure_insight():
    episode = LearningEpisode(
        planner_session_id="planner",
        goal="Reply",
        metrics={
            "planning_memory_outcome": "failure",
            "planning_memory_candidate_id": "template_customer_reply",
        },
    )

    result = LearningEngine().analyze(episode)

    assert any(i.code == "planning_memory:failure" for i in result.insights)
