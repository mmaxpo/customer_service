from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WebhookEndpointCreate(BaseModel):
    name: str
    source: str
    workflow_id: UUID | None = None
    secret: str | None = None
    config: dict = Field(default_factory=dict)


class WebhookEndpointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    source: str
    workflow_id: UUID | None = None
    status: str
    config: dict
    created_at: datetime


class WebhookDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    endpoint_id: UUID
    user_id: UUID
    source: str
    event_type: str
    payload: dict
    headers: dict
    job_id: UUID | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
