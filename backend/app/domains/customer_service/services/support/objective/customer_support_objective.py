from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field


class CustomerSupportAction(StrEnum):
    WHOLE_REFUND = "whole_refund"
    PARTIAL_REFUND = "partial_refund"
    REPLACEMENT = "replacement"
    REPLACEMENT_ADDRESS = "replacement_address"


class MissingInformation(StrEnum):
    REFUND_ITEM = "refund_item"
    REPLACEMENT_ITEM = "replacement_item"
    REPLACEMENT_ADDRESS = "replacement_address"


class CustomerSupportObjective(BaseModel):
    order_ref: str | None = None

    issues: list[str] = Field(default_factory=list)
    requested_actions: list[CustomerSupportAction] = Field(
        default_factory=list
    )

    urgency: str = "normal"

    item_assignments: dict[str, str | None] = Field(
        default_factory=lambda: {
            "refund_item": None,
            "replacement_item": None,
        }
    )
    replacement_address: dict | None = None

    missing_information: list[MissingInformation] = Field(
        default_factory=list
    )

    requires_clarification: bool = False
    mutation_allowed: bool = False


class CustomerSupportObjectiveInterpreter:
    """
    Customer-service domain interpretation.

    This service identifies a customer's business objective before a
    provider-specific workflow or capability is selected. It must not
    perform Shopify or other provider operations.
    """

    _ORDER_REF = re.compile(
        r"(?:order\s*)?#?([0-9]{3,})",
        re.IGNORECASE,
    )

    def interpret(self, message: str) -> CustomerSupportObjective:
        value = message.strip()
        lowered = value.lower()

        order_ref = self._extract_order_ref(value)

        issues: list[str] = []
        requested_actions: list[CustomerSupportAction] = []
        missing_information: list[MissingInformation] = []

        if any(word in lowered for word in ("damaged", "broken", "defective")):
            issues.append("damaged_items")

        refund_requested = any(
            phrase in lowered
            for phrase in (
                "refund",
                "refunded",
                "money back",
            )
        )
        replacement_requested = any(
            phrase in lowered
            for phrase in (
                "replace",
                "replaced",
                "replacement",
                "reship",
                "send another",
            )
        )

        address_change_requested = (
            replacement_requested
            and any(
                phrase in lowered
                for phrase in (
                    "new address",
                    "changed my address",
                    "different address",
                    "change the address",
                )
            )
        )

        partial_refund_requested = (
            refund_requested
            and any(
                phrase in lowered
                for phrase in (
                    "one item",
                    "an item",
                    "this item",
                    "that item",
                    "item refunded",
                    "refund the ",
                    "refund my ",
                )
            )
        )

        if refund_requested:
            requested_actions.append(
                CustomerSupportAction.PARTIAL_REFUND
                if partial_refund_requested
                else CustomerSupportAction.WHOLE_REFUND
            )

        if replacement_requested:
            requested_actions.append(
                CustomerSupportAction.REPLACEMENT
            )

        if address_change_requested:
            requested_actions.append(
                CustomerSupportAction.REPLACEMENT_ADDRESS
            )

        urgency = (
            "high"
            if any(
                word in lowered
                for word in (
                    "urgent",
                    "asap",
                    "immediately",
                    "right away",
                )
            )
            else "normal"
        )

        # Whole-order refunds do not require an item assignment.
        # Partial refunds must identify the exact line item before review.
        if partial_refund_requested:
            missing_information.append(
                MissingInformation.REFUND_ITEM
            )

        if replacement_requested:
            missing_information.append(
                MissingInformation.REPLACEMENT_ITEM
            )

        if address_change_requested:
            missing_information.append(
                MissingInformation.REPLACEMENT_ADDRESS
            )

        return CustomerSupportObjective(
            order_ref=order_ref,
            issues=issues,
            requested_actions=requested_actions,
            urgency=urgency,
            missing_information=missing_information,
            requires_clarification=bool(missing_information),
            mutation_allowed=False,
        )

    def _extract_order_ref(self, message: str) -> str | None:
        match = self._ORDER_REF.search(message)

        if match is None:
            return None

        return match.group(1)
