from app.tcos.planner.runtime.intent import PlannerIntentName, detect_intent


def test_detect_customer_reply_intent():
    intent = detect_intent(text="Reply to the customer about damaged order refund")

    assert intent.name == PlannerIntentName.CUSTOMER_REPLY
    assert intent.confidence > 0.7
    assert intent.needs_clarification is False


def test_detect_unknown_intent():
    intent = detect_intent(text="Build a quarterly revenue forecast")

    assert intent.name == PlannerIntentName.UNKNOWN
    assert intent.needs_clarification is True


def test_planner_runtime_records_intent_event():
    from app.tcos.planner.runtime import PlannerRuntime

    session = PlannerRuntime().plan_goal(goal="Reply to customer")

    assert "IntentDetected" in [event.type for event in session.events]
