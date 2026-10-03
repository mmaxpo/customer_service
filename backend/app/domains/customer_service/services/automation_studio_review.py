"""Automation studio review job methods."""

from __future__ import annotations

# The job mixins intentionally share the service module's dependency surface;
# keeping the moved methods verbatim is what makes this a behavior-only split.
# ruff: noqa: F401

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.providers.llm.factory import build_generate_llm_client
from app.core.providers.llm.resilience import LLMProviderError
from app.domains.customer_service.models.omnichannel import CustomerServiceEventSubscription
from app.domains.customer_service.models.quality import CustomerServiceQualityReview
from app.domains.customer_service.models.workflows import CustomerServiceWorkflowTemplate
from app.node_registration import register_application_nodes
from app.runtime.validation import validate_workflow
from app.runtime.nodes.registry.core import list_registered_nodes
from app.workflow_operations.versions.repository import WorkflowVersionRepository

from .automation_studio_helpers import (
    NODE_LIBRARY,
    catalog as get_catalog,
    diff,
    edit_summary,
    graph_view,
    humanize,
    needs_approval,
    node_type as get_node_type,
    step_name,
    truncate,
    validate,
)
from .automation_studio_json import parse_json

RUN_FLAG_REVIEW_TYPE = "run_flag"


class ReviewStudioMixin:
    _RUNS_SQL = """
        SELECT r.workflow_run_id, r.thread_id, r.status, r.created_at, r.updated_at,
               r.extra, job.subscription_id, job.subscription_name, job.version,
               job.customer_message, job.final_run_id,
               EXISTS (
                 SELECT 1 FROM workflow_run_events e
                 WHERE e.workflow_run_id = r.workflow_run_id
                   AND (e.event->'meta'->>'handoff_required' = 'true'
                        OR e.event->>'event' = 'node_error')
               ) AS had_problem,
               (SELECT count(*) FROM cs_quality_reviews q
                 WHERE q.user_id = r.user_id AND q.review_type = :flag_type
                   AND q.outcome = 'open'
                   AND q.issues->0->>'run_id' = r.workflow_run_id::text) AS open_flags,
               EXISTS (SELECT 1 FROM cs_quality_reviews q
                 WHERE q.user_id = r.user_id AND q.review_type = :flag_type
                   AND q.outcome = 'dismissed'
                   AND q.issues->0->>'run_id' = r.workflow_run_id::text) AS dismissed
        FROM workflow_runs r
        LEFT JOIN LATERAL (
          SELECT j.payload->'extras'->'subscription'->>'id' AS subscription_id,
                 j.payload->'extras'->'subscription'->>'name' AS subscription_name,
                 j.payload->'extras'->'workflow_version' AS version,
                 j.payload->>'message' AS customer_message,
                 j.result->'meta'->>'workflow_run_id' AS final_run_id
          FROM platform_jobs j
          WHERE j.user_id = r.user_id AND j.job_type = 'workflow.run'
            AND (j.result->'meta'->>'workflow_run_id' = r.workflow_run_id::text
                 OR (j.payload->>'thread_id' = r.thread_id::text
                     AND j.created_at <= r.created_at))
          ORDER BY (j.result->'meta'->>'workflow_run_id' = r.workflow_run_id::text) DESC NULLS LAST,
                   j.created_at DESC
          LIMIT 1
        ) job ON true
        WHERE r.user_id = :workspace_id
    """

    async def _recent_conversations(self, workspace_id: UUID, subscription_id: UUID) -> list[dict]:
        # Real past answers from this workflow, shown as the "before" side.
        result = await self.db.execute(
            text(
                """
                SELECT r.workflow_run_id, r.thread_id, r.status, r.created_at,
                  (SELECT m.body FROM cs_conversation_messages m
                    WHERE m.conversation_id = r.thread_id AND m.sender_type = 'customer'
                      AND m.created_at <= r.created_at
                    ORDER BY m.created_at DESC LIMIT 1) AS customer_message,
                  (SELECT m.body FROM cs_conversation_messages m
                    WHERE m.conversation_id = r.thread_id AND m.sender_type = 'ai'
                      AND m.created_at >= r.created_at
                    ORDER BY m.created_at ASC LIMIT 1) AS answer
                FROM platform_jobs j
                JOIN workflow_runs r
                  ON r.workflow_run_id::text = j.result->'meta'->>'workflow_run_id'
                WHERE j.user_id = :workspace_id
                  AND j.job_type = 'workflow.run'
                  AND j.payload->'extras'->'subscription'->>'id' = :subscription_id
                ORDER BY r.created_at DESC
                LIMIT 5
                """
            ),
            {"workspace_id": workspace_id, "subscription_id": str(subscription_id)},
        )
        return [
            {
                "run_id": str(row.workflow_run_id),
                "conversation_id": str(row.thread_id) if row.thread_id else None,
                "status": row.status,
                "created_at": row.created_at,
                "customer_message": row.customer_message,
                "answer": row.answer,
            }
            for row in result
        ]

    @staticmethod
    def _run_summary(row) -> dict:
        reasons = []
        if row.open_flags:
            reasons.append("flagged")
        if not row.dismissed:
            if row.status == "failed":
                reasons.append("failed")
            elif row.had_problem:
                reasons.append("handed_over")
        return {
            "run_id": str(row.workflow_run_id),
            "conversation_id": str(row.thread_id) if row.thread_id else None,
            "status": row.status,
            "workflow_id": row.subscription_id,
            "workflow_name": row.subscription_name,
            "version": row.version,
            "created_at": row.created_at,
            "customer_message": truncate(row.customer_message),
            "review_reasons": reasons,
        }

    async def review_queue(self, *, workspace_id: UUID) -> list[dict]:
        result = await self.db.execute(
            text(
                self._RUNS_SQL
                + """
                  AND r.created_at > now() - interval '30 days'
                ORDER BY r.created_at DESC
                LIMIT 100
                """
            ),
            {"workspace_id": workspace_id, "flag_type": RUN_FLAG_REVIEW_TYPE},
        )
        # A retried job leaves one run per attempt; only its final run counts.
        runs = [
            self._run_summary(row)
            for row in result
            if not row.final_run_id or row.final_run_id == str(row.workflow_run_id)
        ]
        return [run for run in runs if run["review_reasons"]]

    @staticmethod
    def _run_steps(events) -> tuple[list[dict], str | None]:
        steps: dict[str, dict] = {}
        for event, created_at in events:
            node_id = event.get("node_id")
            if not node_id:
                continue
            step = steps.setdefault(node_id, {"node_id": node_id, "status": "queued"})
            kind = event.get("event")
            if kind == "node_start":
                step.update(status="running", started_at=created_at)
            elif kind == "node_end":
                meta = event.get("meta") or {}
                step.update(
                    status="done",
                    ended_at=created_at,
                    output=truncate(event.get("output")),
                    meta=meta,
                    problem="handoff_required" if meta.get("handoff_required") else None,
                )
            elif kind == "node_skip":
                step.update(status="skipped", reason=event.get("reason"))
            elif kind == "node_error":
                step.update(
                    status="error",
                    ended_at=created_at,
                    error=truncate(event.get("error") or event.get("message")),
                    problem="error",
                )
        for step in steps.values():
            if step.get("started_at") and step.get("ended_at"):
                step["duration_ms"] = round(
                    (step["ended_at"] - step["started_at"]).total_seconds() * 1000
                )
        likely_cause = next(
            (s["node_id"] for s in steps.values() if s.get("problem") == "error"), None
        ) or next((s["node_id"] for s in steps.values() if s.get("problem")), None)
        return list(steps.values()), likely_cause

    async def _run_transcript(self, *, workspace_id: UUID, thread_id) -> list[dict]:
        if not thread_id:
            return []
        messages = await self.db.execute(
            text(
                """
                SELECT m.id, m.sender_type, m.body, m.created_at
                FROM cs_conversation_messages m
                JOIN cs_conversations c ON c.id = m.conversation_id
                WHERE m.conversation_id = :conversation_id AND c.user_id = :workspace_id
                ORDER BY m.created_at
                """
            ),
            {"conversation_id": thread_id, "workspace_id": workspace_id},
        )
        return [
            {
                "id": str(m.id),
                "sender": str(m.sender_type.value if hasattr(m.sender_type, "value") else m.sender_type),
                "body": m.body,
                "created_at": m.created_at,
            }
            for m in messages
        ]

    async def _run_flags(self, *, workspace_id: UUID, run_id: UUID) -> list[dict]:
        flags = await self.db.execute(
            select(CustomerServiceQualityReview).where(
                CustomerServiceQualityReview.user_id == workspace_id,
                CustomerServiceQualityReview.review_type == RUN_FLAG_REVIEW_TYPE,
                CustomerServiceQualityReview.outcome == "open",
            )
        )
        return [
            {"id": str(flag.id), **(flag.issues or [{}])[0], "created_at": flag.created_at}
            for flag in flags.scalars()
            if (flag.issues or [{}])[0].get("run_id") == str(run_id)
        ]

    async def run_detail(self, *, workspace_id: UUID, run_id: UUID) -> dict:
        result = await self.db.execute(
            text(self._RUNS_SQL + " AND r.workflow_run_id = :run_id"),
            {"workspace_id": workspace_id, "run_id": run_id, "flag_type": RUN_FLAG_REVIEW_TYPE},
        )
        row = result.first()
        if row is None:
            raise HTTPException(status_code=404, detail="Run not found")

        workflow = (
            await self.db.execute(
                text("SELECT workflow FROM workflow_runs WHERE workflow_run_id = :id"),
                {"id": run_id},
            )
        ).scalar_one()
        events = (
            await self.db.execute(
                text(
                    """
                    SELECT event, created_at FROM workflow_run_events
                    WHERE workflow_run_id = :id ORDER BY id
                    """
                ),
                {"id": run_id},
            )
        ).all()

        steps, likely_cause = self._run_steps(events)
        if likely_cause is None and row.status == "failed":
            failed = ((row.extra or {}).get("failed_node") or {}).get("id")
            likely_cause = failed if failed in {step["node_id"] for step in steps} else None

        transcript = await self._run_transcript(workspace_id=workspace_id, thread_id=row.thread_id)
        run_flags = await self._run_flags(workspace_id=workspace_id, run_id=run_id)

        return {
            **self._run_summary(row),
            "failure": (row.extra or {}).get("error"),
            "elapsed_sec": (row.extra or {}).get("elapsed_sec"),
            "graph": graph_view(workflow, get_catalog()),
            "steps": steps,
            "likely_cause": likely_cause,
            "transcript": transcript,
            "flags": run_flags,
        }

    async def flag_run(
        self,
        *,
        workspace_id: UUID,
        reviewer_id: UUID,
        run_id: UUID,
        step_id: str | None,
        message_id: str | None,
        note: str,
    ) -> dict:
        run = await self.run_detail(workspace_id=workspace_id, run_id=run_id)
        if not run["conversation_id"]:
            raise HTTPException(status_code=409, detail="This run has no conversation to flag.")
        flag = CustomerServiceQualityReview(
            user_id=workspace_id,
            conversation_id=UUID(run["conversation_id"]),
            overall_score=0.0,
            issues=[
                {"run_id": str(run_id), "step_id": step_id, "message_id": message_id, "note": note}
            ],
            reviewer_type="human",
            reviewer_id=reviewer_id,
            review_type=RUN_FLAG_REVIEW_TYPE,
            outcome="open",
        )
        self.db.add(flag)
        await self.db.commit()
        return {"id": str(flag.id)}

    async def dismiss_run(self, *, workspace_id: UUID, reviewer_id: UUID, run_id: UUID) -> None:
        """"Not a problem": close open flags and keep the run out of the queue."""
        run = await self.run_detail(workspace_id=workspace_id, run_id=run_id)
        await self.db.execute(
            text(
                """
                UPDATE cs_quality_reviews SET outcome = 'dismissed'
                WHERE user_id = :workspace_id AND review_type = :flag_type
                  AND outcome = 'open' AND issues->0->>'run_id' = :run_id
                """
            ),
            {"workspace_id": workspace_id, "flag_type": RUN_FLAG_REVIEW_TYPE, "run_id": str(run_id)},
        )
        if run["conversation_id"] and not run["flags"]:
            self.db.add(
                CustomerServiceQualityReview(
                    user_id=workspace_id,
                    conversation_id=UUID(run["conversation_id"]),
                    overall_score=1.0,
                    issues=[{"run_id": str(run_id), "note": "Not a problem"}],
                    reviewer_type="human",
                    reviewer_id=reviewer_id,
                    review_type=RUN_FLAG_REVIEW_TYPE,
                    outcome="dismissed",
                )
            )
        await self.db.commit()
