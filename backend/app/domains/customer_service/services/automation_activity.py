from __future__ import annotations

import hashlib
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.services.timeline import ConversationTimelineService
from app.workflow_operations.timeline.service import WorkflowTimelineService


_SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "cookie",
    "password",
    "refresh_token",
    "secret",
    "token",
}


class CustomerServiceAutomationActivityService:
    """Frontend projection over product and core agent-runtime evidence."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(
        self,
        *,
        workspace_id: UUID,
        conversation_id: UUID,
        categories: set[str] | None = None,
        limit: int = 100,
    ) -> dict:
        source_limit = min(max(limit * 2, 50), 300)
        timeline = await ConversationTimelineService(self.db).get_timeline(
            user_id=workspace_id,
            conversation_id=conversation_id,
            limit=source_limit,
        )
        items = [self._from_product_event(item) for item in timeline]

        # Expand a bounded number of workflow runs into their core evidence.
        run_ids: list[str] = []
        for item in timeline:
            run_id = (item.get("metadata") or {}).get("workflow_run_id")
            if run_id and run_id not in run_ids:
                run_ids.append(run_id)
            if len(run_ids) >= 10:
                break
        workflow_timeline = WorkflowTimelineService(self.db)
        for run_id in run_ids:
            runtime = await workflow_timeline.get_timeline(
                workflow_run_id=UUID(run_id), user_id=workspace_id
            )
            for item in runtime.get("items") or []:
                normalized = self._from_runtime_event(run_id, item)
                if normalized is not None:
                    items.append(normalized)

        if categories:
            items = [item for item in items if item["category"] in categories]
        items.sort(key=lambda item: item["timestamp"], reverse=True)
        has_more = len(items) > limit
        items = items[:limit]
        counts: dict[str, int] = {}
        for item in items:
            counts[item["category"]] = counts.get(item["category"], 0) + 1
        return {
            "conversation_id": str(conversation_id),
            "items": items,
            "counts": counts,
            "has_more": has_more,
        }

    def _from_product_event(self, event: dict) -> dict:
        event_type = event["type"]
        metadata = event.get("metadata") or {}
        text = f"{event_type} {event.get('title') or ''} {metadata.get('status') or ''}".lower()
        category = self._category(text)
        if event_type in {"message", "internal_note", "tag_added", "ticket_assigned"}:
            category = "conversation"
        elif event_type in {"insight_generated", "suggested_action"}:
            category = "ai_decision"
        elif event_type == "workflow_execution":
            category = "failure_retry" if self._is_failure(text) else "workflow_execution"
        elif event_type == "audit_log" and str(event.get("title", "")).startswith("autopilot."):
            category = "ai_decision"
        entity_id = event.get("entity_id")
        return {
            "id": self._id("product", event_type, entity_id, event["timestamp"]),
            "category": category,
            "type": event_type,
            "timestamp": event["timestamp"],
            "title": event["title"],
            "description": event.get("description"),
            "status": metadata.get("status"),
            "actor_id": str(event["actor_id"]) if event.get("actor_id") else None,
            "workflow_run_id": metadata.get("workflow_run_id"),
            "entity_type": event.get("entity_type"),
            "entity_id": str(entity_id) if entity_id else None,
            "details": self._sanitize(metadata),
        }

    def _from_runtime_event(self, run_id: str, item: dict) -> dict | None:
        timestamp = item.get("created_at")
        if not timestamp:
            return None
        parsed_timestamp = datetime.fromisoformat(timestamp)
        event_type = str(item.get("type") or "runtime_event")
        node_type = str(item.get("node_type") or "")
        text = f"{event_type} {node_type}".lower()
        category = self._category(text)
        payload = self._sanitize(item.get("payload") or {})
        status = payload.get("status") or (payload.get("state_summary") or {}).get("status")
        return {
            "id": self._id("runtime", run_id, item.get("source"), item.get("seq")),
            "category": category,
            "type": event_type,
            "timestamp": parsed_timestamp,
            "title": self._title(category, event_type, node_type),
            "description": payload.get("message") or payload.get("error"),
            "status": str(status) if status is not None else None,
            "actor_id": None,
            "workflow_run_id": run_id,
            "entity_type": "workflow_runtime_event",
            "entity_id": None,
            "details": {
                "source": item.get("source"),
                "seq": item.get("seq"),
                "node_id": item.get("node_id"),
                "node_type": item.get("node_type"),
                "payload": payload,
            },
        }

    def _category(self, text: str) -> str:
        if any(value in text for value in ["approval", "human.", "interrupt", "wait"]):
            return "approval"
        if any(value in text for value in ["repair", "replan", "replay"]):
            return "repair"
        if any(value in text for value in ["verification", "verify", "outcome"]):
            return "verification"
        if any(value in text for value in ["learn", "insight", "observation"]):
            return "learned_insight"
        if self._is_failure(text):
            return "failure_retry"
        if any(value in text for value in ["provider", "capability", "tool.", "shopify"]):
            return "provider_call"
        if any(value in text for value in ["decision", "classif", "intent", "agent"]):
            return "ai_decision"
        return "workflow_execution"

    def _is_failure(self, text: str) -> bool:
        return any(value in text for value in ["failed", "failure", "error", "retry", "dead_letter"])

    def _title(self, category: str, event_type: str, node_type: str) -> str:
        labels = {
            "ai_decision": "AI decision",
            "workflow_execution": "Workflow execution",
            "provider_call": "Provider call",
            "approval": "Approval",
            "failure_retry": "Failure or retry",
            "verification": "Verification",
            "repair": "Repair",
            "learned_insight": "Learned insight",
        }
        detail = node_type or event_type
        return f"{labels.get(category, 'Activity')}: {detail}"

    def _sanitize(self, value):
        if isinstance(value, dict):
            return {
                key: "[redacted]" if key.lower() in _SENSITIVE_KEYS else self._sanitize(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._sanitize(item) for item in value]
        return value

    def _id(self, *parts) -> str:
        raw = ":".join(str(part) for part in parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

