from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.engine.persistence.postgres import PostgresRunStore
from app.workflow_operations.snapshots.service import WorkflowSnapshotService


class WorkflowTimelineService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.run_store = PostgresRunStore(db)
        self.snapshots = WorkflowSnapshotService(db)

    async def get_timeline(
        self,
        *,
        workflow_run_id: UUID,
        user_id: UUID,
    ) -> dict:
        run = await self.run_store.get_run_public(run_id=workflow_run_id)
        if not run or run.get("user_id") != user_id:
            return {
                "workflow_run_id": str(workflow_run_id),
                "status": "not_found",
                "items": [],
            }

        events = await self.run_store.list_events(
            run_id=workflow_run_id,
            limit=500,
            after_seq=0,
        )

        snapshots = await self.snapshots.list_for_run(
            workflow_run_id=workflow_run_id,
            user_id=user_id,
        )

        items = []

        for event_row in events:
            event = event_row.get("event") or {}
            items.append(
                {
                    "source": "event",
                    "seq": event_row.get("seq") or event_row.get("id"),
                    "type": event.get("event") or "event",
                    "node_id": event.get("node_id"),
                    "node_type": event.get("node_type"),
                    "payload": event,
                    "created_at": (
                        event_row["created_at"].isoformat()
                        if event_row.get("created_at")
                        else None
                    ),
                }
            )

        for snapshot in snapshots:
            items.append(
                {
                    "source": "snapshot",
                    "seq": snapshot.seq,
                    "type": snapshot.snapshot_type,
                    "node_id": snapshot.node_id,
                    "node_type": snapshot.node_type,
                    "payload": {
                        "event": snapshot.event,
                        "state_summary": self._state_summary(snapshot.state),
                    },
                    "created_at": (
                        snapshot.created_at.isoformat() if snapshot.created_at else None
                    ),
                }
            )

        items.sort(
            key=lambda item: (
                item.get("created_at") or "",
                item.get("seq") or 0,
                item.get("source") or "",
            )
        )

        return {
            "workflow_run_id": str(workflow_run_id),
            "status": run.get("status"),
            "thread_id": str(run.get("thread_id")) if run.get("thread_id") else None,
            "created_at": run["created_at"].isoformat()
            if run.get("created_at")
            else None,
            "updated_at": run["updated_at"].isoformat()
            if run.get("updated_at")
            else None,
            "items": items,
            "counts": {
                "events": len(events),
                "snapshots": len(snapshots),
                "items": len(items),
            },
        }

    def _state_summary(self, state: dict) -> dict:
        meta = state.get("meta") or {}
        return {
            "status": meta.get("status") or state.get("status"),
            "last": state.get("last"),
            "finished": sorted(list(meta.get("finished") or [])),
            "skipped": sorted(list(meta.get("skipped") or [])),
            "vars_keys": sorted(list((state.get("vars") or {}).keys())),
            "results_keys": sorted(list((state.get("results") or {}).keys())),
            "errors_keys": sorted(list((state.get("errors") or {}).keys())),
            "interrupt": meta.get("interrupt"),
            "replay": meta.get("replay"),
        }
