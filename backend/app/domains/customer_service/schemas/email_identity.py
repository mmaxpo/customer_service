from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmailIdentityUpdate(BaseModel):
    from_name: str = Field(min_length=1, max_length=120)
    from_email: str = Field(min_length=3, max_length=320)
    reply_to: str | None = Field(default=None, max_length=320)
    provider_domain_id: str | None = Field(default=None, max_length=255)

    @field_validator("from_email", "reply_to")
    @classmethod
    def validate_email(cls, value: str | None):
        if value is not None and (
            "@" not in value or value.startswith("@") or value.endswith("@")
        ):
            raise ValueError("Invalid email address")
        return value.lower() if value else value


class EmailIdentityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID
    from_name: str
    from_email: str
    reply_to: str | None
    provider_domain_id: str | None
    verification_status: str
    verified_at: datetime | None
