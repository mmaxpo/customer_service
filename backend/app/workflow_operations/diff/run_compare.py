from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow_operations.diff.service import WorkflowStateDiffService
from app.workflow_operations.snapshots.service import WorkflowSnapshotService


class WorkflowRunCompareService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.snapshots = WorkflowSnapshotService(db)
        self.diff = WorkflowStateDiffService()

    async def compare_runs(
        self,
        *,
        baseline_run_id: UUID,
        candidate_run_id: UUID,
        user_id: UUID | None = None,
    ) -> dict:
        baseline = await self.snapshots.list_for_run(
            workflow_run_id=baseline_run_id,
            user_id=user_id,
        )
        candidate = await self.snapshots.list_for_run(
            workflow_run_id=candidate_run_id,
            user_id=user_id,
        )

        if not baseline or not candidate:
            return {
                "status": "not_found",
                "baseline_run_id": str(baseline_run_id),
                "candidate_run_id": str(candidate_run_id),
            }

        baseline_final = self._final_snapshot(baseline)
        candidate_final = self._final_snapshot(candidate)

        final_state_diff = self.diff.compare_states(
            before=baseline_final.state,
            after=candidate_final.state,
        )

        return {
            "status": "ok",
            "baseline_run_id": str(baseline_run_id),
            "candidate_run_id": str(candidate_run_id),
            "baseline_snapshot_count": len(baseline),
            "candidate_snapshot_count": len(candidate),
            "final_state_changed": final_state_diff["changed"],
            "final_state_diff": final_state_diff,
            "node_output_changes": self._compare_node_outputs(
                baseline=baseline,
                candidate=candidate,
            ),
        }

    def _final_snapshot(self, snapshots):
        completed = [
            item for item in snapshots if item.snapshot_type == "run_completed"
        ]
        if completed:
            return completed[-1]
        return snapshots[-1]

    def _compare_node_outputs(self, *, baseline, candidate) -> list[dict]:
        baseline_outputs = self._node_outputs(baseline)
        candidate_outputs = self._node_outputs(candidate)

        node_ids = sorted(set(baseline_outputs) | set(candidate_outputs))
        changes = []

        for node_id in node_ids:
            before = baseline_outputs.get(node_id)
            after = candidate_outputs.get(node_id)

            if before != after:
                changes.append(
                    {
                        "node_id": node_id,
                        "before": before,
                        "after": after,
                    }
                )

        return changes

    def _node_outputs(self, snapshots) -> dict:
        outputs = {}

        for snapshot in snapshots:
            if snapshot.snapshot_type != "node_end":
                continue

            if not snapshot.node_id:
                continue

            event = snapshot.event or {}
            outputs[snapshot.node_id] = event.get("output")

        return outputs
