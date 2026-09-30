from types import SimpleNamespace

from app.runtime.engine.context import RuntimeContext
from app.runtime.resources import (
    BusinessServices,
    RuntimeServiceFactory,
    get_runtime_services,
)


def test_runtime_context_builds_services_with_legacy_aliases():
    db = object()
    tools = object()
    run_store = object()
    event_sink = object()
    request = SimpleNamespace(
        state=SimpleNamespace(tools=tools),
        app=SimpleNamespace(),
    )

    ctx = RuntimeContext(
        request=request,
        user_id="user_1",
        thread_id="thread_1",
        db=db,
        extras={},
        run_store=run_store,
        event_sink=event_sink,
    )

    assert ctx.db is ctx.services.data.db
    assert ctx.tools is ctx.services.ai.tools
    assert ctx.run_store is ctx.services.runtime.run_store
    assert ctx.event_sink is ctx.services.infrastructure.event_sink
    assert ctx.user_id == ctx.services.identity.user_id
    assert ctx.thread_id == ctx.services.identity.thread_id


def test_get_runtime_services_backfills_from_legacy_context():
    db = object()
    tools = object()
    ctx = SimpleNamespace(
        db=db,
        tools=tools,
        user_id="user_1",
        thread_id="thread_1",
        run_store=None,
        event_sink=None,
        request=None,
    )

    services = get_runtime_services(ctx)

    assert services.data.db is db
    assert services.ai.tools is tools
    assert services.identity.user_id == "user_1"
    assert services.identity.thread_id == "thread_1"


def test_get_runtime_services_repairs_incomplete_services():
    db = object()
    tools = object()
    services = RuntimeContext(
        request=SimpleNamespace(
            state=SimpleNamespace(tools=None), app=SimpleNamespace()
        ),
        user_id="user_1",
        thread_id="thread_1",
        db=None,
    ).services

    ctx = SimpleNamespace(
        services=services,
        db=db,
        tools=tools,
        user_id="user_1",
        thread_id="thread_1",
        run_store=None,
        event_sink=None,
        request=None,
    )

    repaired = get_runtime_services(ctx)

    assert repaired is services
    assert repaired.data.db is db
    assert repaired.ai.tools is tools


def test_runtime_context_accepts_prebuilt_services():
    db = object()
    marker = object()

    services = RuntimeServiceFactory.build(
        db=db,
        business=BusinessServices(
            shopify=marker,
        ),
    )

    request = SimpleNamespace(
        state=SimpleNamespace(
            tools=None,
        ),
        app=SimpleNamespace(),
    )

    ctx = RuntimeContext(
        request=request,
        user_id="user_1",
        thread_id="thread_1",
        db=db,
        services=services,
    )

    assert ctx.services is services
    assert ctx.services.business.shopify is marker
