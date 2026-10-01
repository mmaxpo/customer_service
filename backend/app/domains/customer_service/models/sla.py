from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    String,
    func,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domains.customer_service.models.enums import (
    SLAViolationStatus,
    TicketPriority,
    SLATargetType,
)
from app.models.models import Base


class SLAPolicy(Base):
    __tablename__ = "cs_sla_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority),
        nullable=False,
    )

    first_response_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    business_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    calendar_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cs_sla_calendars.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SLAViolation(Base):
    __tablename__ = "cs_sla_violations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_tickets.id"), index=True, nullable=False
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cs_sla_policies.id"), nullable=True
    )

    target_type: Mapped[SLATargetType] = mapped_column(
        Enum(
            SLATargetType,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            name="slatargettype",
        ),
        nullable=False,
    )

    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    breached_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    status: Mapped[SLAViolationStatus] = mapped_column(
        Enum(
            SLAViolationStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            name="slaviolationstatus",
        ),
        default=SLAViolationStatus.OPEN,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
