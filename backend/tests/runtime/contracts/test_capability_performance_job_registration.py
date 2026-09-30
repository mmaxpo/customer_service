from app.platform.composition import (
    build_default_event_registry,
    build_default_job_registry,
)
from app.runtime.capabilities.execution import (
    CAPABILITY_EXECUTION_COMPLETED_EVENT,
)


def test_capability_event_handler_is_registered():
    handlers = build_default_event_registry().handlers_for(
        CAPABILITY_EXECUTION_COMPLETED_EVENT
    )

    assert any(
        handler.__name__ == "enqueue_capability_performance_projection"
        for handler in handlers
    )


def test_capability_projection_job_handler_is_registered():
    assert (
        build_default_job_registry().get("capability.performance.project") is not None
    )
