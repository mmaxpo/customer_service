from pathlib import Path

from app.cognitive_runtime import (
    build_application_cognitive_runtime,
)
from app.tcos.cognitive import CognitiveRuntime


def test_raw_cognitive_runtime_remains_core_only():
    runtime = CognitiveRuntime()

    assert runtime._product_planners is None


def test_application_runtime_installs_customer_service():
    runtime = build_application_cognitive_runtime()

    assert runtime._product_planners is not None

    assert runtime._product_planners.contains(
        "customer_service"
    )


def test_application_runtime_uses_customer_service_product_planner():
    runtime = build_application_cognitive_runtime()

    session = runtime.execute_goal(
        goal="Customer wants order #1001 status",
        user_id="user_1",
    )

    candidate = (
        session.planner_session[
            "selected_candidate"
        ]
    )

    assert (
        candidate["source"]
        == "customer_service_product_planner"
    )

    serialized = session.model_dump_json().lower()

    assert "ecommerce.orders.get" in serialized
    assert "shopify.get_order" not in serialized


def test_core_cognitive_runtime_imports_no_product_implementation():
    text = Path(
        "app/tcos/cognitive/runtime.py"
    ).read_text(
        encoding="utf-8",
    )

    assert "app.domains." not in text
    assert "customer_service" not in text
    assert "shopify" not in text

def test_application_runtime_has_default_semantic_capability_predicate():
    runtime = build_application_cognitive_runtime()

    assert runtime._is_semantic_capability is not None

    assert (
        runtime._is_semantic_capability(
            "ecommerce.orders.get"
        )
        is True
    )

    assert (
        runtime._is_semantic_capability(
            "runtime.response"
        )
        is False
    )


def test_application_runtime_accepts_explicit_semantic_predicate():
    calls: list[str] = []

    def predicate(capability_id: str) -> bool:
        calls.append(capability_id)
        return capability_id == "custom.semantic"

    runtime = build_application_cognitive_runtime(
        is_semantic_capability=predicate,
    )

    assert runtime._is_semantic_capability is predicate

    assert runtime._is_semantic_capability(
        "custom.semantic"
    )

    assert calls == ["custom.semantic"]
