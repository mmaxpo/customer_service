from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.platform.jobs.service import JobService


class PlatformJobEnqueueConfig(BaseModel):
    node_type: Literal["platform.job.enqueue"] = "platform.job.enqueue"

    job_type: str = Field(..., description="Platform job type, e.g. workflow.run")
    payload: dict[str, Any] = Field(default_factory=dict)

    max_attempts: int = Field(default=3, ge=1, le=20)

    save_as: str = Field(
        default="job",
        description="state.vars key where job metadata is stored",
    )


class PlatformJobEnqueueNode:
    async def run(self, ctx, state: dict, config: PlatformJobEnqueueConfig) -> dict:
        if ctx.db is None:
            raise ValueError("platform.job.enqueue requires ctx.db")

        idempotency_key = (
            (getattr(ctx, "node_data", None) or {}).get("_runtime") or {}
        ).get("idempotency_key")
        payload = dict(config.payload or {})
        if idempotency_key:
            payload.setdefault("idempotency_key", idempotency_key)

        job = await JobService(ctx.db).enqueue(
            user_id=ctx.user_id,
            job_type=config.job_type,
            payload=payload,
            max_attempts=config.max_attempts,
        )

        output = {
            "job_id": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
        }

        return {
            "output": output,
            "patch": {
                "vars": {
                    config.save_as: output,
                },
                "last": output,
            },
            "meta": {
                "job_id": str(job.id),
                "job_type": job.job_type,
                "status": job.status,
                "idempotency_key": idempotency_key,
            },
        }
