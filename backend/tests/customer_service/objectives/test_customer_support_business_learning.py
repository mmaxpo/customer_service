from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domains.customer_service.services.support.learning.customer_support_business_learning import (
    CustomerSupportBusinessLearningMapper,
)
from app.runtime.learning import (
    BusinessLearningObservation,
)


def _sources():
    user_id = uuid4()
    outcome_id = uuid4()
    evaluation_id = uuid4()

    outcome = SimpleNamespace(
        id=outcome_id,
        user_id=user_id,
        review_plan_id=str(uuid4()),
        workflow_run_id=uuid4(),
        chat_session_id=uuid4(),
        conversation_id=uuid4(),
        objective_namespace=(
            "customer_service.support"
        ),
        objective_ref=str(uuid4()),
        source_objective_version=1,
        outcome_version=1,
        objective_type="multi_operation",
        order_ref="#1001",
        decision="approved",
        status="mixed",
        operation_count=3,
        customer_message="Refund submitted.",
    )

    evaluation = SimpleNamespace(
        id=evaluation_id,
        user_id=user_id,
        support_outcome_id=outcome_id,
        evaluation_version=1,
        result="partially_achieved",
        reason_code=(
            "completed_and_incomplete_operations"
        ),
        summary=(
            "Some operations completed while "
            "others remain incomplete."
        ),
        confidence=0.9,
        retryable=False,
        achieved_operation_count=1,
        failed_operation_count=0,
        pending_operation_count=2,
        unknown_operation_count=0,
        not_executed_operation_count=0,
        observed_outcome_json={
            "decision": "approved",
            "status": "mixed",
            "operation_count": 3,
        },
        evidence_json=[
            {
                "kind": (
                    "canonical_support_outcome"
                ),
                "source": (
                    "customer_service."
                    "support_outcome"
                ),
                "data": {
                    "sensitive": (
                        "must not be copied"
                    ),
                },
            },
        ],
        created_at=datetime.now(
            timezone.utc
        ),
    )

    event = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        payload={
            "evaluation_id": str(
                evaluation_id
            ),
            "support_outcome_id": str(
                outcome_id
            ),
        },
    )

    return event, outcome, evaluation


def test_maps_support_evaluation_to_business_observation():
    event, outcome, evaluation = _sources()

    observation = (
        CustomerSupportBusinessLearningMapper()
        .build(
            event=event,
            outcome=outcome,
            evaluation=evaluation,
        )
    )

    assert isinstance(
        observation,
        BusinessLearningObservation,
    )

    assert (
        observation.source_event_id
        == event.id
    )
    assert (
        observation
        .source_evaluation_record_id
        == evaluation.id
    )
    assert (
        observation
        .source_outcome_record_id
        == outcome.id
    )

    assert (
        observation.objective_namespace
        == "customer_service.support"
    )
    assert (
        observation.result
        == "partially_achieved"
    )
    assert observation.is_final is True

    assert (
        observation
        .achieved_operation_count
        == 1
    )
    assert (
        observation
        .pending_operation_count
        == 2
    )

    assert (
        observation.context[
            "business_domain"
        ]
        == "customer_service"
    )


def test_mapper_does_not_copy_raw_evidence_data():
    event, outcome, evaluation = _sources()

    observation = (
        CustomerSupportBusinessLearningMapper()
        .build(
            event=event,
            outcome=outcome,
            evaluation=evaluation,
        )
    )

    assert observation.evidence_summary == {
        "count": 1,
        "items": [
            {
                "kind": (
                    "canonical_support_outcome"
                ),
                "source": (
                    "customer_service."
                    "support_outcome"
                ),
            },
        ],
    }

    assert (
        "data"
        not in observation
        .evidence_summary["items"][0]
    )


def test_retryable_evaluation_is_not_final():
    event, outcome, evaluation = _sources()
    evaluation.retryable = True

    observation = (
        CustomerSupportBusinessLearningMapper()
        .build(
            event=event,
            outcome=outcome,
            evaluation=evaluation,
        )
    )

    assert observation.retryable is True
    assert observation.is_final is False


def test_rejects_cross_user_sources():
    event, outcome, evaluation = _sources()
    evaluation.user_id = uuid4()

    with pytest.raises(
        ValueError,
        match="ownership does not match",
    ):
        (
            CustomerSupportBusinessLearningMapper()
            .build(
                event=event,
                outcome=outcome,
                evaluation=evaluation,
            )
        )


def test_rejects_wrong_evaluation_outcome_reference():
    event, outcome, evaluation = _sources()
    evaluation.support_outcome_id = uuid4()

    with pytest.raises(
        ValueError,
        match="does not reference",
    ):
        (
            CustomerSupportBusinessLearningMapper()
            .build(
                event=event,
                outcome=outcome,
                evaluation=evaluation,
            )
        )


def test_rejects_event_evaluation_identity_mismatch():
    event, outcome, evaluation = _sources()

    event.payload["evaluation_id"] = str(
        uuid4()
    )

    with pytest.raises(
        ValueError,
        match="evaluation identity",
    ):
        (
            CustomerSupportBusinessLearningMapper()
            .build(
                event=event,
                outcome=outcome,
                evaluation=evaluation,
            )
        )


def test_contract_rejects_unknown_fields():
    event, outcome, evaluation = _sources()

    observation = (
        CustomerSupportBusinessLearningMapper()
        .build(
            event=event,
            outcome=outcome,
            evaluation=evaluation,
        )
    )

    payload = observation.model_dump()
    payload["unexpected"] = True

    with pytest.raises(ValidationError):
        BusinessLearningObservation(
            **payload
        )
