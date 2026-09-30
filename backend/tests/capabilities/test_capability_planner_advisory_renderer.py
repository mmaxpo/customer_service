from __future__ import annotations

from uuid import uuid4

from app.tcos.capabilities.planner_advisory_policy import (
    CapabilityPlannerAdvisoryContext,
    CapabilityPlannerContextItem,
    CapabilityPlannerContextItemKind,
    CapabilityPlannerContextSource,
)
from app.tcos.capabilities.planner_advisory_renderer import (
    CapabilityPlannerAdvisoryRenderer,
)


def _source():
    return CapabilityPlannerContextSource(
        promotion_id=uuid4(),
        candidate_id=uuid4(),
        evidence_fingerprint="a" * 64,
    )


def _item(*, kind, text, source):
    return CapabilityPlannerContextItem(
        kind=kind,
        text=text,
        source=source,
    )


def test_renderer_returns_empty_contract_for_no_context():
    rendered = (
        CapabilityPlannerAdvisoryRenderer()
        .render(
            CapabilityPlannerAdvisoryContext()
        )
    )

    assert rendered.present is False
    assert rendered.text == ""
    assert (
        rendered.payload["advisory_count"]
        == 0
    )
    assert (
        rendered.informational_only
        is True
    )
    assert rendered.affects_ranking is False
    assert (
        rendered.authorizes_execution
        is False
    )


def test_renderer_produces_deterministic_text_and_payload():
    source = _source()

    context = CapabilityPlannerAdvisoryContext(
        considerations=(
            _item(
                kind=(
                    CapabilityPlannerContextItemKind
                    .CONSIDERATION
                ),
                text=(
                    "Collect the order reference "
                    "before invoking the capability."
                ),
                source=source,
            ),
        ),
        cautions=(
            _item(
                kind=(
                    CapabilityPlannerContextItemKind
                    .CAUTION
                ),
                text=(
                    "Missing order references "
                    "have produced failures."
                ),
                source=source,
            ),
        ),
        constraints=(
            _item(
                kind=(
                    CapabilityPlannerContextItemKind
                    .CONSTRAINT
                ),
                text=(
                    "Human approval remains "
                    "required."
                ),
                source=source,
            ),
        ),
        source_promotion_ids=(
            source.promotion_id,
        ),
        advisory_count=2,
    )

    renderer = (
        CapabilityPlannerAdvisoryRenderer()
    )

    first = renderer.render(context)
    second = renderer.render(context)

    assert first == second
    assert first.present is True

    assert (
        "Learned planner context"
        in first.text
    )
    assert "Considerations" in first.text
    assert "Cautions" in first.text
    assert "Constraints" in first.text
    assert "Provenance" in first.text

    assert (
        "informational only"
        in first.text
    )
    assert (
        str(source.promotion_id)
        in first.text
    )
    assert (
        str(source.candidate_id)
        in first.text
    )
    assert (
        source.evidence_fingerprint
        in first.text
    )

    assert (
        first.payload["advisory_count"]
        == 2
    )
    assert len(
        first.payload["considerations"]
    ) == 1
    assert len(
        first.payload["cautions"]
    ) == 1
    assert len(
        first.payload["constraints"]
    ) == 1

    safety = first.payload["safety"]

    assert safety == {
        "informational_only": True,
        "affects_ranking": False,
        "affects_compatibility": False,
        "selects_provider": False,
        "authorizes_execution": False,
        "bypasses_approval": False,
        "bypasses_verification": False,
    }


def test_renderer_omits_empty_sections():
    source = _source()

    rendered = (
        CapabilityPlannerAdvisoryRenderer()
        .render(
            CapabilityPlannerAdvisoryContext(
                considerations=(
                    _item(
                        kind=(
                            CapabilityPlannerContextItemKind
                            .CONSIDERATION
                        ),
                        text="Consider this.",
                        source=source,
                    ),
                ),
                source_promotion_ids=(
                    source.promotion_id,
                ),
                advisory_count=1,
            )
        )
    )

    assert "Considerations" in rendered.text
    assert "Cautions" not in rendered.text
    assert "Constraints" not in rendered.text
