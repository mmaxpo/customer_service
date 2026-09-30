from app.core.session import SessionLocal
from app.runtime.capabilities.execution import (
    DatabaseProviderHealthReader,
    NullProviderHealthReader,
)
from app.runtime.resources import RuntimeServiceFactory


def test_factory_without_db_uses_null_health_reader():
    services = RuntimeServiceFactory.build(
        user_id="user_1",
    )

    assert isinstance(
        services.capabilities.resolver
        .provider_health_reader,
        NullProviderHealthReader,
    )


def test_factory_with_db_uses_database_health_reader():
    # Construction does not perform database I/O.
    services = RuntimeServiceFactory.build(
        db=SessionLocal(),
        user_id="user_1",
    )

    assert isinstance(
        services.capabilities.resolver
        .provider_health_reader,
        DatabaseProviderHealthReader,
    )
