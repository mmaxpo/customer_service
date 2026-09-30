from app.runtime.capabilities.execution import (
    ProviderHealthEnforcementMode,
)
from app.runtime.resources import RuntimeServiceFactory


def test_factory_defaults_to_shadow_health_mode():
    services = RuntimeServiceFactory.build(
        user_id="user_1",
    )

    assert (
        services.capabilities.resolver
        .provider_health_mode
        == ProviderHealthEnforcementMode.SHADOW
    )


def test_factory_accepts_explicit_enforcement_mode():
    services = RuntimeServiceFactory.build(
        user_id="user_1",
        provider_health_mode="enforce_unhealthy",
    )

    assert (
        services.capabilities.resolver
        .provider_health_mode
        == ProviderHealthEnforcementMode
        .ENFORCE_UNHEALTHY
    )
