from app.tcos.planner.runtime.capability_reasoner import (
    CapabilityReasoner,
)
from app.tcos.planner.runtime.intent import (
    detect_intent,
)
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)


def test_reasoner_selects_generic_url_summary():
    message = (
        "Please summarize "
        "https://example.com/article"
    )

    result = CapabilityReasoner().reason(
        intent=detect_intent(text=message),
        context=PlanningContext(
            user_message=message,
        ),
    )

    assert (
        result.selected_capability
        == "generic.url_summary"
    )

    assert result.required_capabilities == [
        "runtime.web_fetch_extract",
        "runtime.llm_generate",
        "runtime.response",
    ]




def test_reasoner_does_not_plan_order_status_in_core():
    message = "Where is my order #1001?"

    result = CapabilityReasoner().reason(
        intent=detect_intent(text=message),
        context=PlanningContext(
            user_message=message,
        ),
    )

    assert (
        result.selected_capability
        != "customer_service.order_status"
    )

    assert "shopify.get_order" not in (
        result.required_capabilities
    )

    assert "customer_service.extract_order_ref" not in (
        result.required_capabilities
    )
