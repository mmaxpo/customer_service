from types import SimpleNamespace

from app.agents_runtime.usage import UsageTracker, extract_token_usage


def test_extract_openai_responses_usage_shape():
    response = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=100,
            output_tokens=25,
            total_tokens=125,
        )
    )

    usage = extract_token_usage(response)

    assert usage.input_tokens == 100
    assert usage.output_tokens == 25
    assert usage.total_tokens == 125


def test_extract_legacy_usage_shape():
    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
    )

    usage = extract_token_usage(response)

    assert usage.input_tokens == 10
    assert usage.output_tokens == 5
    assert usage.total_tokens == 15


def test_missing_usage_returns_zeroes():
    response = SimpleNamespace()

    usage = extract_token_usage(response)

    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.total_tokens == 0


def test_usage_tracker_accumulates_llm_calls():
    tracker = UsageTracker(agent_run_id="run-1")

    tracker.record_llm_response(
        SimpleNamespace(
            model="gpt-5.5",
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=20,
                total_tokens=120,
            ),
        )
    )

    tracker.record_llm_response(
        SimpleNamespace(
            model="gpt-5.5",
            usage=SimpleNamespace(
                input_tokens=50,
                output_tokens=10,
                total_tokens=60,
            ),
        )
    )

    assert tracker.usage.agent_run_id == "run-1"
    assert tracker.usage.model == "gpt-5.5"
    assert tracker.usage.llm_calls == 2
    assert tracker.usage.input_tokens == 150
    assert tracker.usage.output_tokens == 30
    assert tracker.usage.total_tokens == 180
