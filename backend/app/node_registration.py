from __future__ import annotations

from app.runtime.nodes.registry.builtins import (
    register_core_nodes,
)


def register_application_nodes() -> None:
    """
    Register every workflow-node package installed in this application.

    Core registration is always available.

    Product and provider registrations are imported lazily here so the
    application composition root does not force domain/provider model
    initialization merely by being imported.

    Dependency direction:

        application composition
            -> core
            -> installed products
            -> installed providers

    Core itself never imports Product or Provider implementations.
    """

    register_core_nodes()

    from app.domains.customer_service.runtime.nodes import (
        register_customer_service_nodes,
    )
    from app.providers.shopify.runtime import (
        register_shopify_nodes,
    )

    register_customer_service_nodes()
    register_shopify_nodes()


__all__ = [
    "register_application_nodes",
]
