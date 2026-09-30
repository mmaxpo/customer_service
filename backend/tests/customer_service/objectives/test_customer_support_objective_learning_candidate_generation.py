from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.domains.customer_service.services.support.learning.customer_support_objective_learning_candidate_generation import (
    CustomerSupportObjectiveLearningCandidateGenerationService,
)
from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
    CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
    build_customer_support_objective_learning_profile,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningCandidateFactory,
    ObjectiveLearningCandidateGenerationResult,
    ObjectiveLearningCandidatePolicy,
)


NOW = datetime(
    2026,
    8,
    5,
    12,
    0,
    tzinfo=timezone.utc,
)


class FakeSummaryService:
    def __init__(self, summaries) -> None:
        self.summaries = list(summaries)
        self.calls = []

    async def summarize(self, **kwargs):
        self.calls.append(kwargs)
        return list(self.summaries)


class FakeLifecycle:
    def __init__(self, results) -> None:
        self.results = list(results)
        self.calls = []

    async def propose(
        self,
        *,
        user_id,
        aggregation,
        proposed_at,
    ):
        self.calls.append(
            {
                "user_id": user_id,
                "aggregation": aggregation,
                "proposed_at": proposed_at,
            }
        )

        return self.results.pop(0)


def _aggregation():
    from tests.runtime.contracts.test_objective_learning_lifecycle_operations import (
        _aggregation,
    )

    return _aggregation()


def _generated(
    *,
    policy_version: int,
    created: bool,
):
    candidate = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(
            policy_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF),
            policy_version=policy_version,
            minimum_summary_confidence=0.0,
        )
    ).propose(
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    return ObjectiveLearningCandidateGenerationResult(
        candidate=candidate,
        created=created,
    )


def test_profile_policy_is_mapped_into_generic_policies():
    profile = build_customer_support_objective_learning_profile(
        profile_version=4,
        policy_version=7,
        minimum_confidence=0.96,
        minimum_effective_sample_size=5.0,
        explicit_approval_required=True,
    )

    service = CustomerSupportObjectiveLearningCandidateGenerationService(
        object(),
        profile=profile,
        summary_service=FakeSummaryService([]),
        lifecycle=FakeLifecycle([]),
    )

    assert service.aggregation_policy.minimum_effective_sample_size == 5.0

    assert service.candidate_policy.policy_ref == (
        CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF
    )
    assert service.candidate_policy.policy_version == 7
    assert service.candidate_policy.minimum_summary_confidence == 0.96
    assert service.candidate_policy.explicit_approval_required is True

    assert service.candidate_policy.informational_only is True
    assert service.candidate_policy.affects_ranking is False
    assert service.candidate_policy.affects_capability_selection is False
    assert service.candidate_policy.affects_business_plan is False
    assert service.candidate_policy.selects_provider is False
    assert service.candidate_policy.authorizes_execution is False
    assert service.candidate_policy.bypasses_approval is False
    assert service.candidate_policy.bypasses_verification is False


@pytest.mark.asyncio
async def test_generate_scopes_summary_to_exact_profile():
    user_id = uuid4()
    tenant_id = "tenant-generation"
    summary = _aggregation()

    first = _generated(
        policy_version=1,
        created=True,
    )
    second = _generated(
        policy_version=1,
        created=False,
    )

    summary_service = FakeSummaryService([summary, summary])
    lifecycle = FakeLifecycle([first, second])

    service = CustomerSupportObjectiveLearningCandidateGenerationService(
        object(),
        summary_service=summary_service,
        lifecycle=lifecycle,
    )

    result = await service.generate(
        user_id=user_id,
        tenant_id=tenant_id,
        window_hours=48,
        now=NOW,
    )

    assert summary_service.calls == [
        {
            "user_id": user_id,
            "window_hours": 48,
            "tenant_id": tenant_id,
            "objective_namespace": (CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE),
            "objective_type": (CUSTOMER_SUPPORT_OBJECTIVE_TYPE),
            "profile_ref": (CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF),
            "profile_version": 1,
            "now": NOW,
        }
    ]

    assert lifecycle.calls == [
        {
            "user_id": user_id,
            "aggregation": summary,
            "proposed_at": NOW,
        },
        {
            "user_id": user_id,
            "aggregation": summary,
            "proposed_at": NOW,
        },
    ]

    assert result.analyzed_summaries == 2
    assert result.created_candidates == 1
    assert result.existing_candidates == 1
    assert len(result.items) == 2
    assert result.items[0].created is True
    assert result.items[1].created is False


@pytest.mark.asyncio
async def test_generate_with_no_evidence_returns_empty_result():
    summary_service = FakeSummaryService([])

    service = CustomerSupportObjectiveLearningCandidateGenerationService(
        object(),
        summary_service=summary_service,
        lifecycle=FakeLifecycle([]),
    )

    result = await service.generate(
        user_id=uuid4(),
        now=NOW,
    )

    assert result.analyzed_summaries == 0
    assert result.created_candidates == 0
    assert result.existing_candidates == 0
    assert result.items == ()


def test_disabled_profile_cannot_generate_candidates():
    profile = build_customer_support_objective_learning_profile(enabled=False)

    with pytest.raises(
        ValueError,
        match="must be enabled",
    ):
        CustomerSupportObjectiveLearningCandidateGenerationService(
            object(),
            profile=profile,
            summary_service=FakeSummaryService([]),
            lifecycle=FakeLifecycle([]),
        )
