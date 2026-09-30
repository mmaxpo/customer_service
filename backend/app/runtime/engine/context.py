from __future__ import annotations

from typing import Any, Optional

from app.runtime.resources import RuntimeServiceFactory

from app.runtime.resources import RuntimeServices


class RuntimeContext:
    """
    Request-scoped context passed into every workflow node.

    RuntimeContext is the bridge between FastAPI and the workflow runtime.
    It gives nodes access to app-level services without coupling nodes directly
    to FastAPI route handlers.

    Nodes can access:
        ctx.request
        ctx.app
        ctx.user_id
        ctx.thread_id
        ctx.db
        ctx.extras
        ctx.run_store
        ctx.event_sink
        ctx.workflow_run_id
        ctx.tools

    Common ctx.tools contents:
        - LLM clients
        - knowledge search tools
        - web search tools
        - MCP tools
        - extractors

    Example:
        async def run(self, ctx, state, config):
            user_id = ctx.user_id
            db = ctx.db
            retrieve = ctx.tools.retrieve_tool
    """

    def __init__(
        self,
        request: Any,
        user_id: str,
        thread_id: str,
        db: Any,
        extras: Optional[dict] = None,
        *,
        run_store: Any = None,
        event_sink: Any = None,
        workflow_run_id: Optional[str] = None,
        services: RuntimeServices | None = None,
    ):
        """
        Create a runtime context for one workflow execution.

        Args:
            request:
                FastAPI request object.

            user_id:
                Authenticated user id.

            thread_id:
                Conversation/thread id used for workflow continuity.

            db:
                Database session or database dependency.

            extras:
                Optional runtime extras, such as resume input:
                    {"resume_input": {"approved": True}}
                    resume_workflow_run_id: Existing paused workflow run id to resume.

            run_store:
                Optional persistence adapter for workflow_runs.

            event_sink:
                Optional event sink for workflow_run_events.

            workflow_run_id:
                Optional existing workflow run id.
        """
        self.request = request
        self.user_id = user_id
        self.thread_id = thread_id
        self.db = db
        self.extras = extras or {}
        self.run_store = run_store
        self.event_sink = event_sink
        self.workflow_run_id = workflow_run_id
        self.tools = getattr(request.state, "tools", None)
        self.services = (
            services
            if services is not None
            else RuntimeServiceFactory.build(
                request=request,
                db=db,
                tools=self.tools,
                user_id=user_id,
                thread_id=thread_id,
                run_store=run_store,
                event_sink=event_sink,
                extras=self.extras,
            )
        )

    @property
    def app(self):
        """
        Return the FastAPI app instance.

        This allows nodes to access shared app state when needed:

            ctx.app.state.some_service

        Example:
            model = ctx.app.state.llm
        """
        return self.request.app
