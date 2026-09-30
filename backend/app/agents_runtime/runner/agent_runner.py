from __future__ import annotations

from app.agents_runtime.events import (
    AgentEventStore,
    AgentEventStream,
    EventRecorder,
)
from app.agents_runtime.runner.context import AgentRuntimeContext
from app.agents_runtime.runner.loop import (
    continue_after_approval,
    run_tool_agent_loop,
)
from app.agents_runtime.state import AgentState, AgentStateStore
from app.agents_runtime.tools import ToolExecutor, ToolRegistry
from app.agents_runtime.usage import UsageTracker
from app.agents_runtime.usage.budget import UsageBudget
from app.core.providers.llm import AgentLLMClientProtocol as LLMClientProtocol


class AgentRunner:
    def __init__(
        self,
        *,
        llm: LLMClientProtocol,
        tool_registry: ToolRegistry,
        event_store: AgentEventStore | None = None,
        event_stream: AgentEventStream | None = None,
        state_store: AgentStateStore | None = None,
        usage_budget: UsageBudget | None = None,
        max_steps: int = 8,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
        verbosity: str | None = None,
    ) -> None:
        self.llm = llm
        self.tool_registry = tool_registry
        self.tool_executor = ToolExecutor(tool_registry)
        self.event_store = event_store
        self.event_stream = event_stream
        self.state_store = state_store
        self.usage_budget = usage_budget
        self.max_steps = max_steps
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort
        self.verbosity = verbosity

    async def _publish_and_persist_events(self, recorder: EventRecorder) -> None:
        events = recorder.events

        if self.event_store:
            await self.event_store.append_many(events)

        if self.event_stream:
            for event in events:
                await self.event_stream.publish(event)

    async def _persist_state(self, state: AgentState) -> None:
        if self.state_store:
            await self.state_store.save(state)

    async def run(
        self,
        *,
        user_input: str,
        system_prompt: str = "You are a careful AI agent. Use tools when needed.",
        tool_names: list[str] | None = None,
        context: AgentRuntimeContext | None = None,
        usage_budget: UsageBudget | None = None,
        max_steps: int | None = None,
    ) -> tuple[AgentState, EventRecorder]:
        context = context or AgentRuntimeContext()
        state = AgentState(agent_run_id=context.agent_run_id)
        recorder = EventRecorder()

        usage_tracker = UsageTracker(agent_run_id=context.agent_run_id)

        state = await run_tool_agent_loop(
            llm=self.llm,
            tool_registry=self.tool_registry,
            tool_executor=self.tool_executor,
            state=state,
            context=context,
            recorder=recorder,
            system_prompt=system_prompt,
            user_input=user_input,
            tool_names=tool_names,
            max_steps=max_steps or self.max_steps,
            usage_tracker=usage_tracker,
            usage_budget=usage_budget or self.usage_budget,
            max_output_tokens=self.max_output_tokens,
            reasoning_effort=self.reasoning_effort,
            verbosity=self.verbosity,
        )
        state.meta["usage"] = usage_tracker.usage.model_dump()
        await self._persist_state(state)
        await self._publish_and_persist_events(recorder)

        return state, recorder

    async def resume_after_approval(
        self,
        *,
        state: AgentState,
        approved: bool,
        rejection_reason: str | None = None,
        tool_names: list[str] | None = None,
        context: AgentRuntimeContext | None = None,
        usage_budget: UsageBudget | None = None,
        max_steps: int | None = None,
    ) -> tuple[AgentState, EventRecorder]:
        context = context or AgentRuntimeContext(agent_run_id=state.agent_run_id)
        recorder = EventRecorder()
        usage_tracker = UsageTracker(agent_run_id=context.agent_run_id)
        state = await continue_after_approval(
            llm=self.llm,
            tool_registry=self.tool_registry,
            tool_executor=self.tool_executor,
            state=state,
            context=context,
            recorder=recorder,
            approved=approved,
            rejection_reason=rejection_reason,
            tool_names=tool_names,
            max_steps=max_steps or self.max_steps,
            usage_tracker=usage_tracker,
            usage_budget=usage_budget or self.usage_budget,
            max_output_tokens=self.max_output_tokens,
            reasoning_effort=self.reasoning_effort,
            verbosity=self.verbosity,
        )
        state.meta["usage"] = usage_tracker.usage.model_dump()
        await self._persist_state(state)
        await self._publish_and_persist_events(recorder)

        return state, recorder
