from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ShippingTrackRequest(BaseModel):
    tracking_number: str
    provider: str = "generic"


class ShippingTrackingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    tracking_number: str
    status: str | None = None
    payload: dict
    created_at: datetime
