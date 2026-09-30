from pydantic import BaseModel


class CustomerServiceAnalytics(BaseModel):
    total_customers: int
    total_conversations: int
    open_tickets: int
    pending_tickets: int
    closed_tickets: int
    urgent_tickets: int
    open_sla_breaches: int = 0


class WorkloadReportItem(BaseModel):
    assigned_to: str
    open_or_pending_tickets: int
