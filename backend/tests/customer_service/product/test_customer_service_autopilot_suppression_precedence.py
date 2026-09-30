from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domains.customer_service.schemas.autopilot import (
    AutopilotEvaluationRequest,
    AutopilotPolicyWrite,
)
from app.domains.customer_service.services.autopilot import (
    CustomerServiceAutopilotService,
)


@pytest.mark.parametrize("action_kind", ["reply", "mutation"])
@pytest.mark.parametrize(
    "mode,is_enabled",
    [
        ("never_automate", True),
        ("auto_send_safe", False),
    ],
    ids=["never_automate_policy", "disabled_policy"],
)
def test_suppression_takes_precedence_over_mutation_approval(
    action_kind, mode, is_enabled
):
    policy = SimpleNamespace(
        id=uuid4(),
        **AutopilotPolicyWrite(
            intent="refund_request",
            mode=mode,
            is_enabled=is_enabled,
            mutation_requires_approval=True,
        ).model_dump(),
    )
    request = AutopilotEvaluationRequest(
        intent="refund_request",
        action_kind=action_kind,
        confidence=0.99,
        risk="low",
        channel="email",
        language="en",
    )

    decision = CustomerServiceAutopilotService(None)._apply(policy, request)

    assert decision.decision == "never_automate"
    assert decision.may_send is False
    assert decision.may_execute is False
    assert decision.requires_approval is False
    assert "policy_disabled_or_never" in decision.reason_codes
    assert "mutation_requires_approval" not in decision.reason_codes
