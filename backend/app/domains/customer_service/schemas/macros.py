from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class MacroCreate(BaseModel):
    name: str
    body: str
    is_active: bool = True
    meta: dict | None = None


class MacroUpdate(BaseModel):
    name: str | None = None
    body: str | None = None
    is_active: bool | None = None
    meta: dict | None = None


class MacroRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    body: str
    is_active: bool
    meta: dict | None = None
    created_at: datetime
    updated_at: datetime
