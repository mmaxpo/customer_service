from types import SimpleNamespace

from app.runtime.resources import (
    RuntimeServiceFactory,
    get_runtime_services,
)
from app.runtime_services import (
    build_application_runtime_services,
)


def test_runtime_factory_exposes_task_verification():
    db = object()

    services = RuntimeServiceFactory.build(
        db=db
    )

    assert services.task_verifiers is not None
    assert (
        services.task_verifiers.has(
            "shopify.order_action:cancel"
        )
        is True
    )
    assert services.task_verification is not None
    assert (
        services.task_verification.services
        is services
    )
    # Generic Runtime wires verification infrastructure without
    # installing any Product or Provider implementation.
    assert services.business.shopify is None


def test_application_runtime_installs_shopify_for_task_verification():
    services = build_application_runtime_services(
        db=object(),
    )

    assert services.task_verifiers is not None
    assert services.task_verification is not None
    assert (
        services.task_verification.services
        is services
    )
    assert services.business.shopify is not None
    assert hasattr(
        services.business.shopify,
        "get_order_fresh",
    )


def test_runtime_context_repairs_task_verification():
    db = object()

    services = RuntimeServiceFactory.build(
        db=db
    )

    services.task_verifiers = None
    services.task_verification = None

    ctx = SimpleNamespace(
        services=services,
        db=db,
    )

    repaired = get_runtime_services(ctx)

    assert repaired.task_verifiers is not None
    assert repaired.task_verification is not None
    assert (
        repaired.task_verification.services
        is repaired
    )
