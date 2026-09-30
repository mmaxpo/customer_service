from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime_services import build_application_runtime_context
from app.runtime.execution import execute_workflow_dag


class CustomerServiceWorkflowRuntimeBridge:
    def __init__(
        self,
        *,
        request: Request,
        db: AsyncSession,
        user_id,
        run_store,
        event_sink,
    ):
        self.request = request
        self.db = db
        self.user_id = UUID(str(user_id))
        self.run_store = run_store
        self.event_sink = event_sink

    async def run_reply_suggestion(
        self,
        *,
        thread_id,
        workflow: dict,
        message: str,
    ) -> dict:
        ctx = build_application_runtime_context(
            request=self.request,
            user_id=self.user_id,
            thread_id=UUID(str(thread_id)),
            db=self.db,
            extras={
                "customer_service": True,
                "agent_assist": True,
            },
            run_store=self.run_store,
            event_sink=self.event_sink,
        )

        # Keep trigger.message explicit because some workflow nodes read from
        # trigger.data.input rather than the external message argument.
        for node in workflow.get("nodes", []):
            data = node.get("data") or {}
            if data.get("nodeType") == "trigger.message":
                data["input"] = message

        return await execute_workflow_dag(
            ctx=ctx,
            workflow=workflow,
            message=message,
            strict=True,
            max_steps=20,
            max_concurrency=2,
        )


def extract_workflow_answer(result: dict) -> str:
    if not isinstance(result, dict):
        return ""

    if result.get("answer"):
        return str(result["answer"])

    state = result.get("state") or {}

    if isinstance(state, dict):
        if state.get("last"):
            return str(state["last"])

        vars_ = state.get("vars") or {}
        if isinstance(vars_, dict) and vars_.get("reply_suggestion"):
            return str(vars_["reply_suggestion"])

    return ""
