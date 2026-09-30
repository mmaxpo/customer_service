from types import SimpleNamespace

from app.runtime.resources import (
    RuntimeServiceFactory,
    RuntimeServices,
)


def test_runtime_service_factory_builds_structured_container():
    db = object()
    tools = object()
    run_store = object()
    event_sink = object()

    services = RuntimeServiceFactory.build(
        db=db,
        tools=tools,
        user_id="user_1",
        tenant_id="tenant_1",
        thread_id="thread_1",
        run_store=run_store,
        event_sink=event_sink,
    )

    assert isinstance(services, RuntimeServices)
    assert services.identity.user_id == "user_1"
    assert services.identity.tenant_id == "tenant_1"
    assert services.identity.thread_id == "thread_1"
    assert services.data.db is db
    assert services.ai.tools is tools
    assert services.runtime.run_store is run_store
    assert services.infrastructure.event_sink is event_sink


def test_runtime_service_factory_can_read_tools_from_request_state():
    tools = object()
    request = SimpleNamespace(state=SimpleNamespace(tools=tools))

    services = RuntimeServiceFactory.build(request=request)

    assert services.ai.tools is tools
    assert services.tools is tools


def test_runtime_services_legacy_db_and_tools_aliases():
    db = object()
    tools = object()

    services = RuntimeServiceFactory.build(db=db, tools=tools)

    assert services.db is db
    assert services.tools is tools

    new_db = object()
    new_tools = object()
    services.db = new_db
    services.tools = new_tools

    assert services.data.db is new_db
    assert services.ai.tools is new_tools
