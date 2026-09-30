from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.runtime.capabilities.execution.learning import (
    CapabilityLearningInsightPromotion,
    CapabilityLearningPromotionEventType,
    CapabilityLearningPromotionStatus,
    CapabilityLearningPromotionTarget,
    CapabilityPlannerAdvisoryKind,
    CapabilityPlannerAdvisoryProjection,
)


NOW = datetime(
    2026,
    7,
    19,
    12,
    0,
    tzinfo=timezone.utc,
)


def _promotion(
    *,
    kind=(
        "positive_outcome_pattern"
    ),
    status=CapabilityLearningPromotionStatus.ACTIVE,
    target=(
        CapabilityLearningPromotionTarget
        .PLANNER_ADVISORY
    ),
):
    candidate_id = uuid4()

    return CapabilityLearningInsightPromotion(
        promotion_id=uuid4(),
        event_version=1,
        candidate_id=candidate_id,
        candidate_version=2,
        user_id=uuid4(),
        tenant_id="tenant-a",
        capability_id="ecommerce.orders.get",
        provider_id="shopify",
        provider_ref="shopify.orders.get",
        action="read",
        event_type=(
            CapabilityLearningPromotionEventType
            .PROMOTED
        ),
        status=status,
        promotion_target=target,
        evidence_fingerprint="a" * 64,
        reason="Approved advisory.",
        created_by_user_id=uuid4(),
        created_at=NOW,
        promotion_payload={
            "candidate": {
                "candidate_id": str(
                    candidate_id
                ),
                "candidate_version": 2,
                "kind": kind,
                "scope": {
                    "tenant_id": "tenant-a",
                    "capability_id": (
                        "ecommerce.orders.get"
                    ),
                    "provider_id": "shopify",
                    "provider_ref": (
                        "shopify.orders.get"
                    ),
                    "action": "read",
                },
                "statement": (
                    "This scope has a stable "
                    "observed outcome."
                ),
                "recommended_behavior": (
                    "Surface as advisory context."
                ),
                "limitations": [
                    "Exact scope only."
                ],
            }
        },
    )


def test_positive_promotion_projects_guidance():
    advisory = (
        CapabilityPlannerAdvisoryProjection
        .from_promotion(_promotion())
    )

    assert advisory.advisory_kind == (
        CapabilityPlannerAdvisoryKind
        .GUIDANCE
    )
    assert advisory.read_only is True
    assert advisory.affects_ranking is False
    assert (
        advisory.authorizes_execution
        is False
    )
    assert (
        advisory.bypasses_verification
        is False
    )


def test_negative_promotion_projects_warning():
    advisory = (
        CapabilityPlannerAdvisoryProjection
        .from_promotion(
            _promotion(
                kind=(
                    "negative_outcome_pattern"
                )
            )
        )
    )

    assert advisory.advisory_kind == (
        CapabilityPlannerAdvisoryKind
        .WARNING
    )


def test_projection_rejects_non_planner_target():
    with pytest.raises(
        ValueError,
        match="not planner_advisory",
    ):
        (
            CapabilityPlannerAdvisoryProjection
            .from_promotion(
                _promotion(
                    target=(
                        CapabilityLearningPromotionTarget
                        .OPERATOR_GUIDANCE
                    )
                )
            )
        )


def test_projection_rejects_scope_mismatch():
    promotion = _promotion()
    promotion = promotion.model_copy(
        update={
            "provider_id": "other-provider"
        }
    )

    with pytest.raises(
        ValueError,
        match="scope does not match",
    ):
        (
            CapabilityPlannerAdvisoryProjection
            .from_promotion(promotion)
        )
