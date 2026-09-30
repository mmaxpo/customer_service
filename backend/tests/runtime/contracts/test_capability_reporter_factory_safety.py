from app.runtime.resources import RuntimeServiceFactory
from app.runtime.capabilities.execution import (
    NullCapabilityOutcomeReporter,
)


class FakeDB:
    pass


def test_factory_does_not_auto_create_persistent_reporter_from_db():
    services = RuntimeServiceFactory.build(
        db=FakeDB(),
    )

    assert isinstance(
        services.capability_outcome_reporter,
        NullCapabilityOutcomeReporter,
    )
