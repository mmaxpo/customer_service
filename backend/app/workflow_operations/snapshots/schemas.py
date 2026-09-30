from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkflowRunSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_run_id: UUID
    user_id: UUID | None = None
    snapshot_type: str
    node_id: str | None = None
    node_type: str | None = None
    state: dict
    event: dict
    seq: int
    created_at: datetime
