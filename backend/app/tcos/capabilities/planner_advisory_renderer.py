from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.tcos.capabilities.planner_advisory_policy import (
    CapabilityPlannerAdvisoryContext,
    CapabilityPlannerContextItem,
)


class CapabilityPlannerRenderedContext(
    BaseModel
):
    """
    Deterministic representation of informational planner context.

    `text` may later be supplied to an LLM as a context fragment, but this
    contract does not inject it into prompts or authorize any planner/runtime
    behavior.
    """

    model_config = ConfigDict(extra="forbid")

    present: bool
    text: str

    payload: dict = Field(
        default_factory=dict
    )

    informational_only: bool = True
    affects_ranking: bool = False
    affects_compatibility: bool = False
    selects_provider: bool = False
    authorizes_execution: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False

    @model_validator(mode="after")
    def validate_safety_boundary(self):
        if not self.informational_only:
            raise ValueError(
                "Rendered planner context must "
                "remain informational only"
            )

        if any(
            (
                self.affects_ranking,
                self.affects_compatibility,
                self.selects_provider,
                self.authorizes_execution,
                self.bypasses_approval,
                self.bypasses_verification,
            )
        ):
            raise ValueError(
                "Rendered planner context cannot "
                "alter planning or execution"
            )

        if self.present and not self.text.strip():
            raise ValueError(
                "Present rendered context must "
                "contain text"
            )

        if not self.present and self.text:
            raise ValueError(
                "Absent rendered context must "
                "have empty text"
            )

        return self


class CapabilityPlannerAdvisoryRenderer:
    """
    Renders structured advisory context without interpreting or applying it.

    Output order is inherited from the deterministic advisory consumption
    policy. No score, ordering, provider, approval, verification, or execution
    behavior is produced.
    """

    heading = "Learned planner context"

    safety_notice = (
        "This context is informational only. "
        "Do not use it to change capability ranking, compatibility, "
        "provider selection, approval requirements, verification, "
        "or execution authorization."
    )

    def render(
        self,
        context: CapabilityPlannerAdvisoryContext,
    ) -> CapabilityPlannerRenderedContext:
        payload = self._payload(context)

        if context.advisory_count == 0:
            return CapabilityPlannerRenderedContext(
                present=False,
                text="",
                payload=payload,
            )

        sections: list[str] = [
            self.heading,
            self.safety_notice,
        ]

        self._append_section(
            sections=sections,
            title="Considerations",
            items=context.considerations,
        )
        self._append_section(
            sections=sections,
            title="Cautions",
            items=context.cautions,
        )
        self._append_section(
            sections=sections,
            title="Constraints",
            items=context.constraints,
        )

        if context.source_promotion_ids:
            sections.extend(
                [
                    "Provenance",
                    *[
                        f"- promotion_id={value}"
                        for value in (
                            context
                            .source_promotion_ids
                        )
                    ],
                ]
            )

        return CapabilityPlannerRenderedContext(
            present=True,
            text="\n".join(sections),
            payload=payload,
        )

    @staticmethod
    def _append_section(
        *,
        sections: list[str],
        title: str,
        items: tuple[
            CapabilityPlannerContextItem,
            ...,
        ],
    ) -> None:
        if not items:
            return

        sections.append(title)

        for item in items:
            sections.append(
                "- "
                + item.text
                + " "
                + CapabilityPlannerAdvisoryRenderer
                ._source_suffix(item)
            )

    @staticmethod
    def _source_suffix(
        item: CapabilityPlannerContextItem,
    ) -> str:
        return (
            "[promotion_id="
            f"{item.source.promotion_id}; "
            "candidate_id="
            f"{item.source.candidate_id}; "
            "evidence_fingerprint="
            f"{item.source.evidence_fingerprint}]"
        )

    @staticmethod
    def _payload(
        context: CapabilityPlannerAdvisoryContext,
    ) -> dict:
        return {
            "advisory_count": (
                context.advisory_count
            ),
            "considerations": [
                item.model_dump(mode="json")
                for item in context.considerations
            ],
            "cautions": [
                item.model_dump(mode="json")
                for item in context.cautions
            ],
            "constraints": [
                item.model_dump(mode="json")
                for item in context.constraints
            ],
            "source_promotion_ids": [
                str(value)
                for value in (
                    context.source_promotion_ids
                )
            ],
            "safety": {
                "informational_only": True,
                "affects_ranking": False,
                "affects_compatibility": False,
                "selects_provider": False,
                "authorizes_execution": False,
                "bypasses_approval": False,
                "bypasses_verification": False,
            },
        }


__all__ = [
    "CapabilityPlannerAdvisoryRenderer",
    "CapabilityPlannerRenderedContext",
]
