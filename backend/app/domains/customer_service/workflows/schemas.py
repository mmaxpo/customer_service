from enum import StrEnum
from pydantic import BaseModel


class SupportIntent(StrEnum):
    REFUND = "refund"
    SHIPPING = "shipping"
    CANCELLATION = "cancellation"
    DAMAGED_PRODUCT = "damaged_product"
    GENERAL = "general"


class MessageClassification(BaseModel):
    intent: SupportIntent
    confidence: float
    reason: str


class WorkflowAction(BaseModel):
    intent: SupportIntent
    ticket_priority: str
    should_auto_close: bool = False
    requires_human: bool = True
