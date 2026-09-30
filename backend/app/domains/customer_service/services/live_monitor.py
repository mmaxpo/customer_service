"""
Live: what needs attention now, and a plain-language log of what the
automation did. Read-only over conversations, runs and waits.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Latest problem recorded on a run: a step error, or a step that asked for a
# person (e.g. the AI provider was down and the customer got the standby reply).
_PROBLEM_SQL = """
    (SELECT coalesce(e.event->>'error', e.event->'meta'->>'provider_failure_code', 'handoff')
       FROM workflow_run_events e
      WHERE e.workflow_run_id = r.workflow_run_id
        AND (e.event->>'event' = 'node_error'
             OR e.event->'meta'->>'handoff_required' = 'true')
      ORDER BY e.id
      LIMIT 1)
"""

# One workflow job per customer message. The worker retries a failing job, and
# every attempt is its own run, so the log reads jobs and shows the final run
# (or, when every attempt failed, the last attempt).
_FINAL_RUN_SQL = """
    LEFT JOIN LATERAL (
      SELECT r.workflow_run_id, r.status, r.user_id
      FROM workflow_runs r
      WHERE r.user_id = j.user_id
        AND (r.workflow_run_id::text = j.result->'meta'->>'workflow_run_id'
             OR (j.result->'meta'->>'workflow_run_id' IS NULL
                 AND r.thread_id::text = j.payload->>'thread_id'
                 AND r.created_at >= j.created_at
                 AND r.created_at <= coalesce(j.finished_at, now())))
      ORDER BY r.created_at DESC
      LIMIT 1
    ) r ON true
"""


def plain_reason(problem: str | None) -> str | None:
    """Turn a recorded error or failure code into one sentence a store owner understands."""
    if not problem:
        return None
    lowered = problem.lower()
    if "llm" in lowered or "openai" in lowered or problem == "handoff":
        return "The AI provider isn't responding, so the customer got the standby reply."
    if "no enabled provider binding" in lowered and "orders" in lowered:
        return "Order lookup isn't set up for this store."
    if "requires a resolved workflow approval" in lowered:
        return "An order change was tried without approval, so it was blocked."
    if "shopify" in lowered:
        return "Shopify returned an error."
    return problem[:160]


def _outcome(job_status: str, run_status: str | None, problem: str | None) -> str:
    if job_status in {"failed", "dead_letter"} or run_status == "failed":
        return "failed"
    if job_status in {"queued", "running"} or run_status == "running":
        return "running"
    if run_status == "paused":
        return "waiting_approval"
    return "handed_over" if problem else "answered"


class LiveMonitorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def activity(
        self,
        *,
        workspace_id: UUID,
        days: int = 7,
        outcome: str | None = None,
        workflow_id: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        result = await self.db.execute(
            text(
                f"""
                SELECT j.status AS job_status, j.attempts, j.created_at, j.error_message,
                       j.payload->>'thread_id' AS conversation_id,
                       j.payload->>'message' AS customer_message,
                       j.payload->'extras'->'subscription'->>'id' AS workflow_id,
                       coalesce(j.payload->'extras'->'subscription'->>'name',
                                j.payload->'workflow'->>'name') AS workflow_name,
                       j.payload->'extras'->'workflow_version' AS version,
                       r.workflow_run_id, r.status AS run_status,
                       c.channel,
                       {_PROBLEM_SQL} AS problem
                FROM platform_jobs j
                {_FINAL_RUN_SQL}
                LEFT JOIN cs_conversations c
                  ON c.id::text = j.payload->>'thread_id' AND c.user_id = j.user_id
                WHERE j.user_id = :workspace_id
                  AND j.job_type = 'workflow.run'
                  AND j.created_at > now() - make_interval(days => :days)
                  AND (CAST(:workflow_id AS text) IS NULL
                       OR j.payload->'extras'->'subscription'->>'id' = :workflow_id)
                ORDER BY j.created_at DESC
                LIMIT :limit
                """
            ),
            {"workspace_id": workspace_id, "days": days, "workflow_id": workflow_id, "limit": limit},
        )
        rows = []
        for row in result:
            problem = row.problem or row.error_message
            row_outcome = _outcome(row.job_status, row.run_status, problem)
            if outcome and row_outcome != outcome:
                continue
            rows.append(
                {
                    "run_id": str(row.workflow_run_id) if row.workflow_run_id else None,
                    "conversation_id": row.conversation_id if row.channel else None,
                    "created_at": row.created_at,
                    "attempts": row.attempts,
                    "channel": row.channel,
                    "customer_message": row.customer_message,
                    "workflow_id": row.workflow_id,
                    "workflow_name": row.workflow_name,
                    "version": row.version,
                    "outcome": row_outcome,
                    "reason": plain_reason(problem),
                }
            )
        return rows

    async def now(self, *, workspace_id: UUID) -> dict:
        return {
            "waiting_for_person": await self._waiting_for_person(workspace_id),
            "approvals_waiting": await self._approvals_waiting(workspace_id),
            "running": await self._running(workspace_id),
            "problems": await self._problems(workspace_id),
        }

    async def _waiting_for_person(self, workspace_id: UUID) -> list[dict]:
        # Open conversations where the customer wrote last (ignoring AI replies
        # that handed over), no teammate has replied since, and no automation
        # answered successfully. A minute's grace lets the automation reply.
        result = await self.db.execute(
            text(
                f"""
                WITH open_conversations AS (
                  SELECT c.id, c.channel, cust.name AS customer_name,
                         (SELECT m.created_at FROM cs_conversation_messages m
                           WHERE m.conversation_id = c.id AND m.sender_type = 'customer'
                           ORDER BY m.created_at DESC LIMIT 1) AS last_customer_at,
                         (SELECT m.body FROM cs_conversation_messages m
                           WHERE m.conversation_id = c.id AND m.sender_type = 'customer'
                           ORDER BY m.created_at DESC LIMIT 1) AS last_customer_message,
                         (SELECT max(m.created_at) FROM cs_conversation_messages m
                           WHERE m.conversation_id = c.id AND m.sender_type = 'agent') AS last_agent_at
                  FROM cs_conversations c
                  JOIN cs_customers cust ON cust.id = c.customer_id
                  LEFT JOIN cs_tickets t ON t.conversation_id = c.id
                  WHERE c.user_id = :workspace_id
                    AND c.status = 'OPEN'
                    AND c.merged_into_id IS NULL
                    AND (c.snoozed_until IS NULL OR c.snoozed_until < now())
                    AND (t.id IS NULL OR t.status::text NOT IN ('RESOLVED', 'CLOSED'))
                )
                SELECT oc.*, run.status AS run_status, run.problem
                FROM open_conversations oc
                LEFT JOIN LATERAL (
                  SELECT r.status, {_PROBLEM_SQL} AS problem
                  FROM workflow_runs r
                  WHERE r.user_id = :workspace_id AND r.thread_id = oc.id
                    AND r.created_at >= oc.last_customer_at - interval '5 seconds'
                  ORDER BY r.created_at DESC
                  LIMIT 1
                ) run ON true
                WHERE oc.last_customer_at IS NOT NULL
                  AND oc.last_customer_at < now() - interval '1 minute'
                  AND (oc.last_agent_at IS NULL OR oc.last_agent_at < oc.last_customer_at)
                  AND NOT coalesce(run.status = 'done' AND run.problem IS NULL, false)
                ORDER BY oc.last_customer_at
                LIMIT 50
                """
            ),
            {"workspace_id": workspace_id},
        )
        waiting = []
        for row in result:
            if row.run_status is None:
                reason = "No automation answered this message."
            elif row.run_status == "paused":
                reason = "An action is waiting for approval."
            else:
                reason = plain_reason(row.problem) or "The automation couldn't finish."
            waiting.append(
                {
                    "conversation_id": str(row.id),
                    "customer_name": row.customer_name,
                    "channel": row.channel,
                    "last_customer_message": (row.last_customer_message or "")[:200],
                    "waiting_since": row.last_customer_at,
                    "reason": reason,
                }
            )
        return waiting

    async def _approvals_waiting(self, workspace_id: UUID) -> list[dict]:
        result = await self.db.execute(
            text(
                """
                SELECT id, workflow_run_id, payload, created_at
                FROM workflow_waits
                WHERE user_id = :workspace_id AND status = 'waiting'
                ORDER BY created_at
                LIMIT 50
                """
            ),
            {"workspace_id": workspace_id},
        )
        return [
            {
                "id": str(row.id),
                "run_id": row.workflow_run_id,
                "question": (row.payload or {}).get("question"),
                "created_at": row.created_at,
            }
            for row in result
        ]

    async def _running(self, workspace_id: UUID) -> int:
        result = await self.db.execute(
            text(
                """
                SELECT count(*) FROM platform_jobs
                WHERE user_id = :workspace_id AND job_type = 'workflow.run'
                  AND status IN ('queued', 'running')
                  AND created_at > now() - interval '1 hour'
                """
            ),
            {"workspace_id": workspace_id},
        )
        return result.scalar_one()

    async def _problems(self, workspace_id: UUID) -> list[dict]:
        # What went wrong in the last 24 hours, grouped into plain reasons.
        rows = await self.activity(workspace_id=workspace_id, days=1, limit=500)
        grouped: dict[str, dict] = {}
        for row in rows:
            if row["outcome"] not in {"failed", "handed_over"} or not row["reason"]:
                continue
            entry = grouped.setdefault(
                row["reason"],
                {"reason": row["reason"], "count": 0, "last_at": row["created_at"], "example_run_id": row["run_id"]},
            )
            entry["count"] += 1
        return sorted(grouped.values(), key=lambda p: p["count"], reverse=True)
