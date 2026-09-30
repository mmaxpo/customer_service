from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.domains.customer_service.models import CustomerStatus


class CustomerCreate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    custom_fields: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, max_length=100
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if value is None:
            return None

        normalized = str(value).strip().lower()
        return normalized or None

    @model_validator(mode="after")
    def require_identity(self):
        name = (self.name or "").strip()
        phone = (self.phone or "").strip()

        if self.email is None and not name and not phone:
            raise ValueError("customer requires at least one of name, email, or phone")

        self.name = name or None
        self.phone = phone or None
        return self


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    status: CustomerStatus | None = None
    custom_fields: dict[str, str | int | float | bool | None] | None = None


class CustomerRead(BaseModel):
    id: uuid.UUID
    name: str | None
    email: str | None
    phone: str | None
    status: CustomerStatus
    custom_fields: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
