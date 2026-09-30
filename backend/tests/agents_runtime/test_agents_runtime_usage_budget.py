from app.agents_runtime.usage.budget import (
    UsageBudget,
    UsageBudgetExceeded,
)
from app.agents_runtime.usage.schemas import AgentRunUsage


def test_budget_allows_usage_under_limit():
    budget = UsageBudget(
        max_total_tokens=1000,
        max_llm_calls=10,
    )

    usage = AgentRunUsage(
        agent_run_id="run-1",
        llm_calls=3,
        total_tokens=500,
    )

    budget.check(usage)


def test_budget_raises_when_token_limit_exceeded():
    budget = UsageBudget(max_total_tokens=100)

    usage = AgentRunUsage(
        agent_run_id="run-1",
        llm_calls=1,
        total_tokens=101,
    )

    try:
        budget.check(usage)
        assert False
    except UsageBudgetExceeded as exc:
        assert "Token budget exceeded" in str(exc)


def test_budget_raises_when_llm_call_limit_exceeded():
    budget = UsageBudget(max_llm_calls=2)

    usage = AgentRunUsage(
        agent_run_id="run-1",
        llm_calls=3,
        total_tokens=50,
    )

    try:
        budget.check(usage)
        assert False
    except UsageBudgetExceeded as exc:
        assert "LLM call budget exceeded" in str(exc)
