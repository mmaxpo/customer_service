from app.cognitive_runtime import (
    build_application_cognitive_runtime,
)


def test_semantic_order_capability_compiles_to_generic_capability_node():
    session = (
        build_application_cognitive_runtime()
        .execute_goal(
            goal="Customer wants order #1001 status",
            user_id="user_1",
        )
    )

    planner = session.planner_session

    assert planner["status"] == "compiled"

    candidate = planner["selected_candidate"]

    assert (
        candidate["source"]
        == "customer_service_product_planner"
    )

    runtime = (
        planner["compilation"]["execution_graph"]
    )

    lookup = next(
        node
        for node in runtime["nodes"]
        if node["id"] == "lookup_order"
    )

    assert lookup["node_type"] == "capability.invoke"

    assert (
        lookup["config"]["capability_id"]
        == "ecommerce.orders.get"
    )

    assert lookup["config"]["input_from"] == "vars"
    assert lookup["config"]["input_key"] == "order_ref"
    assert lookup["config"]["save_as"] == "commerce_order"

    serialized = session.model_dump_json().lower()

    assert "shopify.get_order" not in serialized
