from app.platform.composition import build_default_job_registry


def test_capability_health_evaluation_handler_is_registered():
    assert build_default_job_registry().get("capability.health.evaluate") is not None
