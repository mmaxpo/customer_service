from types import SimpleNamespace

from app.runtime.engine.context import RuntimeContext
from app.runtime.resources import (
    BusinessServices,
    RuntimeServiceFactory,
    get_runtime_services,
)


def test_factory_accepts_injected_business_services():
    shopify = object()

    business = BusinessServices(
        shopify=shopify,
    )

    services = RuntimeServiceFactory.build(
        db=object(),
        business=business,
    )

    assert services.business is business
    assert services.business.shopify is shopify


def test_generic_factory_does_not_install_shopify():
    services = RuntimeServiceFactory.build(
        db=object(),
    )

    assert services.business.shopify is None


def test_get_runtime_services_does_not_install_provider_services():
    db = object()

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
    )

    assert ctx.services.business.shopify is None

    services = get_runtime_services(
        ctx
    )

    assert services is ctx.services
    assert services.business.shopify is None
