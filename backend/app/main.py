from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.platform import realtime_router
from app.api.router import api_router
from app.core.checkpointer import lifespan_checkpointer
from app.core.config import settings
from app.core.cors import cors_allowed_origins
from app.core.http_safety import (
    RequestBodyLimitMiddleware,
    SecurityBoundaryMiddleware,
)
from app.core.observability import (
    RequestObservabilityMiddleware,
    initialize_observability,
)
from app.core.session import SessionLocal
from app.core.startup_validation import (
    validate_startup_configuration,
)
from app.domains.customer_service.services.knowledge_agent_mcp import (
    build_agent_graph_mcp,
)
from app.node_registration import register_application_nodes
from app.runtime.engine.workflow_repo import WorkflowRepo
from app.runtime.tools import build_tools
from app.platform.realtime.hub import realtime_hub
from app.tools.knowledge.search.langchain import (
    make_retrieve_tool,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_observability()
    validate_startup_configuration(settings)

    app.state.reranker = None
    app.state.retrieve_tool = make_retrieve_tool(
        SessionLocal, reranker=app.state.reranker
    )

    register_application_nodes()
    app.state.workflow_repo = WorkflowRepo()

    app.state.tools = build_tools()

    from app.agents_runtime.services import build_agent_runtime_services

    app.state.agent_runtime_services = build_agent_runtime_services()

    checkpointer_cm = lifespan_checkpointer()
    saver = await checkpointer_cm.__aenter__()

    try:
        app.state.langgraph_saver = saver
        # ✅ Don't try to connect MCP / build agent graph unless explicitly enabled
        if getattr(settings, "ENABLE_MCP_AGENT", False):
            app.state.knowledge_agent = await build_agent_graph_mcp(checkpointer=saver)
        else:
            app.state.knowledge_agent = None
        yield
    finally:
        await realtime_hub.close()
        tools = getattr(app.state, "tools", None)
        if tools and hasattr(tools, "aclose"):
            await tools.aclose()
        await checkpointer_cm.__aexit__(None, None, None)


app = FastAPI(title="Tajeran.ai", lifespan=lifespan)


@app.middleware("http")
async def attach_tools(request: Request, call_next):
    tools = getattr(request.app.state, "tools", None)

    # If startup/lifespan didn't run (common in tests), don't crash.
    if tools is None:
        tools = SimpleNamespace()
        request.app.state.tools = tools

    request.state.tools = tools
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityBoundaryMiddleware)
app.add_middleware(RequestObservabilityMiddleware)
app.add_middleware(
    RequestBodyLimitMiddleware,
    max_bytes=settings.MAX_REQUEST_BODY_BYTES,
)

app.include_router(api_router)
app.include_router(realtime_router)
