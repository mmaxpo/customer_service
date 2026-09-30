from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.domains.customer_service.services.support.commerce.commerce_order import (
    CommerceOrder,
)
from app.domains.customer_service.services.support.objective.customer_support_objective import (
    CustomerSupportAction,
    CustomerSupportObjective,
    MissingInformation,
)


class CustomerSupportResolution(BaseModel):
    objective: CustomerSupportObjective
    resolved_fields: list[str] = Field(default_factory=list)
    unresolved_fields: list[MissingInformation] = Field(
        default_factory=list
    )
    status: str
    mutation_allowed: bool = False


class CustomerSupportClarificationResolver:
    """
    Resolve customer clarification against a persisted support objective
    and normalized commerce order.

    This service updates interpretation state only. It never executes
    provider capabilities.
    """

    def resolve(
        self,
        *,
        message: str,
        objective: CustomerSupportObjective,
        order: CommerceOrder,
    ) -> CustomerSupportResolution:
        updated = objective.model_copy(deep=True)
        lowered = message.lower()

        resolved_fields: list[str] = []

        refund_item = self._match_item_after_action(
            message=message,
            action_words=("refund", "refunded"),
            order=order,
        )
        replacement_item = self._match_item_after_action(
            message=message,
            action_words=("replace", "replaced", "replacement"),
            order=order,
        )

        if refund_item is not None:
            updated.item_assignments["refund_item"] = (
                refund_item.provider_item_id
                or refund_item.variant_id
                or refund_item.product_id
                or refund_item.title
            )
            resolved_fields.append("refund_item")

        if replacement_item is not None:
            updated.item_assignments["replacement_item"] = (
                replacement_item.provider_item_id
                or replacement_item.variant_id
                or replacement_item.product_id
                or replacement_item.title
            )
            resolved_fields.append("replacement_item")

        replacement_address = self._extract_address(
            message,
            replacement_requested=(
                replacement_item is not None
                or "replacement" in lowered
            ),
        )

        if replacement_address is not None:
            updated.replacement_address = replacement_address
            resolved_fields.append("replacement_address")

        unresolved: list[MissingInformation] = []

        if (
            CustomerSupportAction.PARTIAL_REFUND
            in updated.requested_actions
            and not updated.item_assignments.get("refund_item")
        ):
            unresolved.append(MissingInformation.REFUND_ITEM)

        if (
            CustomerSupportAction.REPLACEMENT
            in updated.requested_actions
            and not updated.item_assignments.get("replacement_item")
        ):
            unresolved.append(MissingInformation.REPLACEMENT_ITEM)

        if (
            CustomerSupportAction.REPLACEMENT_ADDRESS
            in updated.requested_actions
            and not updated.replacement_address
        ):
            unresolved.append(
                MissingInformation.REPLACEMENT_ADDRESS
            )

        updated.missing_information = unresolved
        updated.requires_clarification = bool(unresolved)
        updated.mutation_allowed = False

        return CustomerSupportResolution(
            objective=updated,
            resolved_fields=resolved_fields,
            unresolved_fields=unresolved,
            status=(
                "awaiting_customer"
                if unresolved
                else "ready_for_review"
            ),
            mutation_allowed=False,
        )

    def _match_item_after_action(
        self,
        *,
        message: str,
        action_words: tuple[str, ...],
        order: CommerceOrder,
    ):
        lowered = message.lower()

        action_positions = [
            lowered.find(word)
            for word in action_words
            if lowered.find(word) >= 0
        ]

        if not action_positions:
            return None

        action_position = min(action_positions)

        matches = []

        for item in order.line_items:
            candidates = [
                item.title,
                item.variant_title,
                item.sku,
            ]

            for candidate in candidates:
                if not candidate:
                    continue

                position = lowered.find(str(candidate).lower())

                if position >= action_position:
                    matches.append(
                        (
                            position - action_position,
                            -len(str(candidate)),
                            item,
                        )
                    )

        if not matches:
            return None

        # Prefer the closest item mention after the action word. When
        # multiple item names start at the same position, prefer the
        # longest/more-specific match (for example, "Snowboard Boots"
        # over "Snowboard").
        matches.sort(
            key=lambda value: (
                value[0],
                value[1],
            )
        )
        return matches[0][2]

    def _extract_address(
        self,
        message: str,
        *,
        replacement_requested: bool,
    ) -> dict | None:
        if not replacement_requested:
            return None

        pattern = re.compile(
            r"(?:send(?:\s+the\s+replacement)?\s+to|"
            r"replacement\s+address(?:\s+is)?|"
            r"new\s+address(?:\s+is)?)"
            r"\s*:?\s*(.+)",
            re.IGNORECASE | re.DOTALL,
        )

        match = pattern.search(message)

        if match is None:
            return None

        value = " ".join(match.group(1).split()).strip(" .")

        if len(value) < 8:
            return None

        return {
            "formatted": value,
        }
