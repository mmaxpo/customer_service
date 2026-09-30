import pytest

from app.runtime.resources import RuntimeServiceFactory
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.execution import (
    InMemoryCapabilityOutcomeReporter,
)


class FakeShopify:
    async def get_order(self, *, user_id, order_ref):
        return {
            "user_id": str(user_id),
            "order_name": order_ref,
        }


class FailingReporter:
    async def report(self, outcome):
        raise RuntimeError("reporter unavailable")


@pytest.mark.asyncio
async def test_invoker_reports_exactly_one_successful_outcome():
    reporter = InMemoryCapabilityOutcomeReporter()

    services = RuntimeServiceFactory.build(
        user_id="user_1",
        tenant_id="tenant_1",
        capability_outcome_reporter=reporter,
    )
    services.business.shopify = FakeShopify()

    result = await services.capabilities.resolve(
        CapabilityInvocation(
            capability_id="shopify.get_order",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert len(reporter.outcomes) == 1

    outcome = reporter.outcomes[0]

    assert outcome.correlation_id
    assert outcome.requested_capability_id == (
        "shopify.get_order"
    )
    assert outcome.resolved_capability_id == (
        "ecommerce.orders.get"
    )
    assert outcome.selected_provider_id == "shopify"
    assert outcome.provider_ref == "shopify.get_order"
    assert outcome.ok is True
    assert outcome.user_id is None
    assert outcome.tenant_id == "tenant_1"

    assert result.metadata["execution_outcome"] == (
        outcome.model_dump(mode="json")
    )


@pytest.mark.asyncio
async def test_invoke_path_also_reports_exactly_one_outcome():
    reporter = InMemoryCapabilityOutcomeReporter()

    services = RuntimeServiceFactory.build(
        user_id="user_1",
        capability_outcome_reporter=reporter,
    )
    services.business.shopify = FakeShopify()

    output = await services.capabilities.invoke(
        "shopify.get_order",
        payload={"order_ref": "#1001"},
    )

    assert output["order_name"] == "#1001"
    assert len(reporter.outcomes) == 1


@pytest.mark.asyncio
async def test_failed_invocation_is_reported():
    reporter = InMemoryCapabilityOutcomeReporter()

    services = RuntimeServiceFactory.build(
        user_id="user_1",
        capability_outcome_reporter=reporter,
    )

    result = await services.capabilities.resolve(
        CapabilityInvocation(
            capability_id="unknown.capability",
        )
    )

    assert result.ok is False
    assert len(reporter.outcomes) == 1
    assert reporter.outcomes[0].ok is False
    assert reporter.outcomes[0].error_code == (
        "unknown_capability"
    )


@pytest.mark.asyncio
async def test_reporter_failure_never_changes_execution_result():
    services = RuntimeServiceFactory.build(
        user_id="user_1",
        capability_outcome_reporter=FailingReporter(),
    )
    services.business.shopify = FakeShopify()

    result = await services.capabilities.resolve(
        CapabilityInvocation(
            capability_id="shopify.get_order",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.output["order_name"] == "#1001"


def test_factory_exposes_same_injected_reporter():
    reporter = InMemoryCapabilityOutcomeReporter()

    services = RuntimeServiceFactory.build(
        capability_outcome_reporter=reporter,
    )

    assert services.capability_outcome_reporter is reporter
    assert services.capabilities.outcome_reporter is reporter
