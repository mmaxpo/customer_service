from uuid import uuid4

import pytest

from app.core.session import get_db
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker


@pytest.mark.asyncio
async def test_failed_workflow_marks_job_failed():
    async for db in get_db():
        job = await JobService(db).enqueue(
            user_id=uuid4(),
            job_type="workflow.run",
            payload={
                "workflow": {
                    "nodes": [
                        {"id": "t", "data": {"nodeType": "trigger.message"}},
                        {"id": "bad", "data": {"nodeType": "shopify.get_order"}},
                    ],
                    "edges": [
                        {
                            "source": "t",
                            "target": "bad",
                        }
                    ],
                },
                "message": "where is order #1005",
            },
            max_attempts=1,
        )

        result = await JobWorker(
            db,
            worker_id="workflow-failure-test",
        ).run_once(job_id=job.id)

        assert result.status == "dead_letter"

        break
