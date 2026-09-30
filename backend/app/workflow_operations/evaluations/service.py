from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker
from app.workflow_operations.evaluations.schemas import (
    WorkflowEvaluationCase,
    WorkflowEvaluationCaseResult,
    WorkflowEvaluationRequest,
    WorkflowEvaluationResult,
)


class WorkflowEvaluationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.jobs = JobService(db)

    async def run_evaluation(
        self,
        *,
        user_id,
        request: WorkflowEvaluationRequest,
    ) -> WorkflowEvaluationResult:
        results = []

        for case in request.cases:
            results.append(
                await self._run_case(
                    user_id=user_id,
                    case=case,
                )
            )

        total = len(results)
        passed = sum(1 for item in results if item.passed)
        score = passed / total if total else 0.0

        return WorkflowEvaluationResult(
            name=request.name,
            passed=bool(total and passed == total),
            score=score,
            total_cases=total,
            passed_cases=passed,
            failed_cases=total - passed,
            cases=results,
        )

    async def _run_case(
        self,
        *,
        user_id,
        case: WorkflowEvaluationCase,
    ) -> WorkflowEvaluationCaseResult:
        job = await self.jobs.enqueue(
            user_id=user_id,
            job_type="workflow.run",
            payload={
                "workflow": case.workflow,
                "message": case.message,
                "thread_id": str(uuid4()),
            },
        )

        finished = await JobWorker(
            self.db,
            worker_id=f"eval-worker-{uuid4()}",
        ).run_once(job_id=job.id)

        errors: list[str] = []

        if finished is None:
            return WorkflowEvaluationCaseResult(
                name=case.name,
                passed=False,
                score=0.0,
                expected_answer=case.expected_answer,
                expected_status=case.expected_status,
                job_id=str(job.id),
                errors=["evaluation_job_not_claimed"],
            )

        result = finished.result or {}
        meta = result.get("meta") or {}

        actual_answer = result.get("answer")
        actual_status = meta.get("status")
        workflow_run_id = meta.get("workflow_run_id")

        if finished.status != "succeeded":
            errors.append(f"job_status:{finished.status}")
            if finished.error_message:
                errors.append(finished.error_message)

        if case.expected_status is not None and actual_status != case.expected_status:
            errors.append(
                f"expected_status={case.expected_status}, actual_status={actual_status}"
            )

        if case.expected_answer is not None and actual_answer != case.expected_answer:
            errors.append(
                f"expected_answer={case.expected_answer!r}, actual_answer={actual_answer!r}"
            )

        passed = not errors

        return WorkflowEvaluationCaseResult(
            name=case.name,
            passed=passed,
            score=1.0 if passed else 0.0,
            expected_answer=case.expected_answer,
            actual_answer=actual_answer,
            expected_status=case.expected_status,
            actual_status=actual_status,
            workflow_run_id=str(workflow_run_id) if workflow_run_id else None,
            job_id=str(finished.id),
            errors=errors,
        )
