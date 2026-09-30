from enum import StrEnum


class CustomerStatus(StrEnum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class ConversationStatus(StrEnum):
    OPEN = "open"
    PENDING = "pending"
    RESOLVED = "resolved"


class TicketStatus(StrEnum):
    OPEN = "open"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageSenderType(StrEnum):
    CUSTOMER = "customer"
    AGENT = "agent"
    AI = "ai"
    SYSTEM = "system"
    INTERNAL_NOTE = "internal_note"


class AgentAssistSuggestionStatus(StrEnum):
    GENERATED = "generated"
    EDITED = "edited"
    APPROVED = "approved"
    SENT = "sent"
    REJECTED = "rejected"


class SLATargetType(StrEnum):
    FIRST_RESPONSE = "first_response"
    RESOLUTION = "resolution"


class SLAViolationStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
