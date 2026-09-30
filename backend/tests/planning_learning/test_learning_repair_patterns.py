from app.tcos.planning_learning import LearningEngine
from app.tcos.planning_learning.models import LearningEpisode


def test_learning_engine_extracts_repair_patterns():
    episode = LearningEpisode(
        planner_session_id="planner",
        goal="Reply",
        repair_result={
            "plan": {
                "actions": [
                    {
                        "type": "insert_missing_artifact_producer",
                        "artifact_id": "summary",
                    }
                ]
            }
        },
    )

    result = LearningEngine().analyze(episode)

    codes = {i.code for i in result.insights}

    assert "repair_required" in codes
    assert "repair_pattern:insert_missing_artifact_producer" in codes
    assert "missing_artifact_pattern" in codes
