from app.domains.customer_service.services.support.objective.customer_support_clarification import (
    CustomerSupportClarificationService,
)
from app.domains.customer_service.services.support.objective.customer_support_objective import (
    CustomerSupportObjectiveInterpreter,
    MissingInformation,
)


MESSAGE = (
    "I received both items damaged in order #1003. "
    "I want one item refunded and the other replaced. "
    "Please send the replacement to my new address. "
    "This is urgent."
)


def _objective():
    return CustomerSupportObjectiveInterpreter().interpret(MESSAGE)


def test_complex_request_builds_targeted_clarification():
    clarification = CustomerSupportClarificationService().build(
        objective=_objective(),
        line_items=[
            {
                "title": "Snowboard",
                "variant_title": "158 cm",
                "quantity": 1,
            },
            {
                "title": "Snowboard Boots",
                "variant_title": "Size 10",
                "quantity": 1,
            },
        ],
    )

    assert clarification.required is True

    assert [
        question.field
        for question in clarification.questions
    ] == [
        MissingInformation.REFUND_ITEM,
        MissingInformation.REPLACEMENT_ITEM,
        MissingInformation.REPLACEMENT_ADDRESS,
    ]

    assert clarification.questions[0].options == [
        "Snowboard — 158 cm",
        "Snowboard Boots — Size 10",
    ]
    assert clarification.questions[1].options == [
        "Snowboard — 158 cm",
        "Snowboard Boots — Size 10",
    ]

    assert clarification.customer_message is not None
    assert "order #1003" in clarification.customer_message
    assert "Which item would you like refunded?" in (
        clarification.customer_message
    )
    assert "Which item would you like replaced?" in (
        clarification.customer_message
    )
    assert "What address should we use" in (
        clarification.customer_message
    )


def test_clarification_explicitly_blocks_mutation():
    clarification = CustomerSupportClarificationService().build(
        objective=_objective(),
        line_items=[
            {"title": "Item A", "quantity": 1},
            {"title": "Item B", "quantity": 1},
        ],
    )

    assert (
        "No refund, replacement, or shipping change will be made"
        in clarification.customer_message
    )


def test_clarification_works_without_provider_line_items():
    clarification = CustomerSupportClarificationService().build(
        objective=_objective(),
        line_items=None,
    )

    assert clarification.required is True
    assert clarification.questions[0].options == []
    assert clarification.questions[1].options == []
    assert "Which item would you like refunded?" in (
        clarification.customer_message
    )
