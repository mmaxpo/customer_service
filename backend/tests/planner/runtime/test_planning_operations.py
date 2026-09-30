from app.tcos.planner.operations import OperationType, PlanningOperation


def test_planning_operation_model():

    op = PlanningOperation(
        id="lookup_order",
        capability_id="shopify.get_order",
        operation_type=OperationType.ACQUIRE_INFORMATION,
        purpose="Lookup order",
        inputs=["order_ref"],
        outputs=["shopify_order"],
    )

    assert op.id == "lookup_order"
    assert op.capability_id == "shopify.get_order"
    assert op.inputs == ["order_ref"]
    assert op.outputs == ["shopify_order"]


def test_defaults():

    op = PlanningOperation(
        id="reply",
        capability_id="runtime.response",
        operation_type=OperationType.COMMUNICATE,
        purpose="Reply",
    )

    assert op.inputs == []
    assert op.outputs == []
    assert op.depends_on == []
