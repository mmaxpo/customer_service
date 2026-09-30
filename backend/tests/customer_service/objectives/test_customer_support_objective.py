from app.domains.customer_service.services.support.objective.customer_support_objective import (
    CustomerSupportAction,
    CustomerSupportObjectiveInterpreter,
    MissingInformation,
)


COMPLEX_REQUEST = (
    "I received both items damaged in order #1003. "
    "I want one item refunded and the other replaced. "
    "Please send the replacement to my new address. "
    "This is urgent."
)


def test_complex_customer_request_is_decomposed_before_execution():
    objective = CustomerSupportObjectiveInterpreter().interpret(
        COMPLEX_REQUEST
    )

    assert objective.order_ref == "1003"
    assert objective.issues == ["damaged_items"]

    assert objective.requested_actions == [
        CustomerSupportAction.PARTIAL_REFUND,
        CustomerSupportAction.REPLACEMENT,
        CustomerSupportAction.REPLACEMENT_ADDRESS,
    ]

    assert objective.urgency == "high"

    assert objective.item_assignments == {
        "refund_item": None,
        "replacement_item": None,
    }
    assert objective.replacement_address is None

    assert objective.missing_information == [
        MissingInformation.REFUND_ITEM,
        MissingInformation.REPLACEMENT_ITEM,
        MissingInformation.REPLACEMENT_ADDRESS,
    ]

    assert objective.requires_clarification is True
    assert objective.mutation_allowed is False


def test_complex_request_never_guesses_item_assignments():
    objective = CustomerSupportObjectiveInterpreter().interpret(
        COMPLEX_REQUEST
    )

    assert objective.item_assignments["refund_item"] is None
    assert objective.item_assignments["replacement_item"] is None


def test_complex_request_without_order_still_requires_safe_intake():
    objective = CustomerSupportObjectiveInterpreter().interpret(
        "One damaged item should be refunded and another replaced urgently."
    )

    assert objective.order_ref is None
    assert objective.mutation_allowed is False
    assert objective.requires_clarification is True



def test_whole_order_refund_does_not_require_item_clarification():
    objective = CustomerSupportObjectiveInterpreter().interpret(
        "I want a refund for order #1001."
    )

    assert objective.order_ref == "1001"
    assert objective.requested_actions == [
        CustomerSupportAction.WHOLE_REFUND
    ]
    assert MissingInformation.REFUND_ITEM not in objective.missing_information
    assert objective.requires_clarification is False
    assert objective.mutation_allowed is False


def test_item_specific_refund_remains_partial_and_requires_item():
    objective = CustomerSupportObjectiveInterpreter().interpret(
        "I want one item refunded from order #1001."
    )

    assert objective.requested_actions == [
        CustomerSupportAction.PARTIAL_REFUND
    ]
    assert objective.missing_information == [
        MissingInformation.REFUND_ITEM
    ]
    assert objective.requires_clarification is True
