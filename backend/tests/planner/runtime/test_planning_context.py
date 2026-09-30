from app.tcos.planner.runtime.planning_inputs import (
    build_default_planning_context,
)


def test_default_planning_context():
    ctx = build_default_planning_context(
        user_message="Where is my order?",
    )

    assert ctx.user_message == "Where is my order?"
    assert ctx.enabled_capabilities == []
    assert ctx.execution_constraints == {}
