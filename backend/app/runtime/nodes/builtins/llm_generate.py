from __future__ import annotations

from pydantic import BaseModel, Field

from app.runtime.nodes.types import NodeRunResult, RuntimeContext
from app.core.token_control.token_budget import resolve_max_output_tokens
from app.core.providers.llm.resilience import LLMProviderError


class LlmGenerateConfig(BaseModel):
    # inputs
    prompt: str = ""
    system: str | None = None

    # model controls
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)

    # production token control
    role: str | None = Field(default="final")
    token_budget_mode: str | None = Field(default="cheap")

    # optional: save to vars via engine save_as too, but useful to patch directly
    save_as: str | None = None
    fallback_from_var: str | None = None
    provider_failure_fallback: str | None = None


class LlmGenerateNode:
    """
    Generic LLM generation node.

    Reads prompt from:
        - config.prompt
        - fallback state.vars["input"]

    Uses:
        ctx.tools.llm.generate(...)

    Stores:
        - output text
        - optionally state.vars[save_as]

    Example:
        prompt = "Write a support reply"
        output = "Sure, I can help..."
    """

    async def run(
        self,
        ctx: RuntimeContext,
        state: dict,
        config: LlmGenerateConfig,
    ) -> NodeRunResult:
        vars_ = state.get("vars") or {}

        prompt = (config.prompt or "").strip()
        if not prompt:
            # fallback convention: if prompt missing, use vars.input
            prompt = str(vars_.get("input") or "").strip()

        if not prompt:
            raise ValueError("llm.generate: prompt is empty")

        # tools discovery (tests vs runtime)
        tools = getattr(ctx, "tools", None) or ctx.request.state.tools
        llm = getattr(tools, "llm", None)
        if llm is None:
            raise AttributeError("llm.generate: tools has no 'llm' client")

        max_tokens = resolve_max_output_tokens(
            role=config.role,
            requested_max_output_tokens=config.max_tokens,
            token_budget_mode=config.token_budget_mode,
        )

        try:
            res = await llm.generate(
                prompt=prompt,
                system=config.system,
                model=config.model,
                temperature=config.temperature,
                max_tokens=max_tokens,
            )

            text = (getattr(res, "text", None) or "").strip()
            empty_output_retried = False

            # Reasoning models can consume a small output allowance entirely as
            # reasoning tokens and return no customer-visible content.
            if not text:
                empty_output_retried = True
                retry_max_tokens = max(int(max_tokens or 0), 800)

                res = await llm.generate(
                    prompt=prompt,
                    system=config.system,
                    model=config.model,
                    temperature=config.temperature,
                    max_tokens=retry_max_tokens,
                )

                text = (getattr(res, "text", None) or "").strip()
                max_tokens = retry_max_tokens
        except LLMProviderError as exc:
            job = (getattr(ctx, "extras", None) or {}).get("_job") or {}
            attempt = int(job.get("attempt") or 0)
            max_attempts = int(job.get("max_attempts") or 0)
            final_job_attempt = bool(max_attempts and attempt >= max_attempts)

            if not config.provider_failure_fallback or (
                exc.retryable and not final_job_attempt
            ):
                raise

            text = config.provider_failure_fallback.strip()
            patch = {"vars": {config.save_as: text}} if config.save_as else {}

            return {
                "output": text,
                "patch": patch,
                "meta": {
                    "model": None,
                    "usage": None,
                    "max_tokens": max_tokens,
                    "token_budget_mode": config.token_budget_mode,
                    "role": config.role,
                    "provider_failure_code": exc.code,
                    "provider_retryable": exc.retryable,
                    "degraded": True,
                    "handoff_required": True,
                },
            }

        if not text and config.fallback_from_var:
            fallback_value = vars_
            for part in config.fallback_from_var.split("."):
                if isinstance(fallback_value, dict):
                    fallback_value = fallback_value.get(part)
                else:
                    fallback_value = None
                    break

            if fallback_value:
                raw = str(fallback_value).strip()
                text = raw[:700]

        patch = {}
        if config.save_as:
            patch = {"vars": {config.save_as: text}}

        return {
            "output": text,
            "patch": patch,
            "meta": {
                "model": getattr(res, "model", None),
                "usage": getattr(res, "usage", None),
                "max_tokens": max_tokens,
                "token_budget_mode": config.token_budget_mode,
                "role": config.role,
                "empty_output_retried": empty_output_retried,
                "empty_output_after_retry": not bool(text),
            },
        }
