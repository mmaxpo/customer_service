from uuid import uuid4

import pytest

from app.core.session import get_db
from app.platform.events.publisher import PlatformEventPublisher
from app.platform.jobs.service import JobService
from app.workflow_operations.waits.schemas import WorkflowWaitCreate
from app.workflow_operations.waits.service import WorkflowWaitService


@pytest.mark.asyncio
async def test_duplicate_matching_platform_event_resolves_wait_only_once_and_enqueues_one_resume():
    """
    Harsh production case:

    A provider/webhook/platform event is delivered twice with the same payload.

    Expected:
        - first event resolves the event wait
        - duplicate event finds no waiting wait to resolve
        - only one workflow.resume job is enqueued
    """
    user_id = uuid4()
    workflow_run_id = f"run-duplicate-event-{uuid4()}"

    async for db in get_db():
        wait = await WorkflowWaitService(db).create(
            user_id=user_id,
            payload=WorkflowWaitCreate(
                workflow_run_id=workflow_run_id,
                node_id="wait-event-1",
                wait_type="event",
                payload={
                    "event_type": "shopify.order.updated",
                    "match": {
                        "order_id": "1001",
                    },
                },
            ),
        )

        first = await PlatformEventPublisher(db).publish(
            user_id=user_id,
            event_type="shopify.order.updated",
            source="shopify",
            payload={
                "order_id": "1001",
                "status": "fulfilled",
            },
        )

        second = await PlatformEventPublisher(db).publish(
            user_id=user_id,
            event_type="shopify.order.updated",
            source="shopify",
            payload={
                "order_id": "1001",
                "status": "fulfilled",
            },
        )

        assert any(
            str(wait.id) in item.get("resolved_wait_ids", [])
            for item in first["handler_results"]
        )

        assert not any(
            str(wait.id) in item.get("resolved_wait_ids", [])
            for item in second["handler_results"]
        )

        jobs = await JobService(db).repo.list_for_user(
            user_id=user_id,
            limit=50,
        )

        matching_resume_jobs = [
            job
            for job in jobs
            if job.job_type == "workflow.resume"
            and job.payload["workflow_run_id"] == workflow_run_id
            and job.payload["input"]["wait_id"] == str(wait.id)
        ]

        assert len(matching_resume_jobs) == 1

        saved = await WorkflowWaitService(db).get_for_user(
            user_id=user_id,
            wait_id=wait.id,
        )

        assert saved.status == "resolved"
        assert saved.resolution["event"]["payload"]["order_id"] == "1001"

        break


@pytest.mark.asyncio
async def test_duplicate_manual_wait_resolve_enqueues_resume_only_once():
    """
    Harsh production case:

    Same wait is resolved twice, like a double-click or duplicate API retry.

    Expected:
        - first resolve succeeds and enqueues resume
        - second resolve is rejected
        - no second resume job is created
    """
    user_id = uuid4()
    workflow_run_id = f"run-duplicate-manual-{uuid4()}"

    async for db in get_db():
        wait = await WorkflowWaitService(db).create(
            user_id=user_id,
            payload=WorkflowWaitCreate(
                workflow_run_id=workflow_run_id,
                node_id="approval-1",
                wait_type="approval",
                payload={"question": "Approve?"},
            ),
        )

        first = await WorkflowWaitService(db).resolve(
            user_id=user_id,
            wait_id=wait.id,
            resolution={"approved": True},
            resume=True,
        )

        assert first["resume_job_id"] is not None

        with pytest.raises(Exception):
            await WorkflowWaitService(db).resolve(
                user_id=user_id,
                wait_id=wait.id,
                resolution={"approved": True},
                resume=True,
            )

        jobs = await JobService(db).repo.list_for_user(
            user_id=user_id,
            limit=50,
        )

        matching_resume_jobs = [
            job
            for job in jobs
            if job.job_type == "workflow.resume"
            and job.payload["workflow_run_id"] == workflow_run_id
            and job.payload["input"]["wait_id"] == str(wait.id)
        ]

        assert len(matching_resume_jobs) == 1

        break


@pytest.mark.asyncio
async def test_platform_event_only_resolves_waits_for_same_user():
    first_user_id = uuid4()
    second_user_id = uuid4()

    async for db in get_db():
        first_wait = await WorkflowWaitService(db).create(
            user_id=first_user_id,
            payload=WorkflowWaitCreate(
                workflow_run_id=f"run-first-{uuid4()}",
                node_id="wait-event-first",
                wait_type="event",
                payload={
                    "event_type": "shopify.order.updated",
                    "match": {"order_id": "1001"},
                },
            ),
        )

        second_wait = await WorkflowWaitService(db).create(
            user_id=second_user_id,
            payload=WorkflowWaitCreate(
                workflow_run_id=f"run-second-{uuid4()}",
                node_id="wait-event-second",
                wait_type="event",
                payload={
                    "event_type": "shopify.order.updated",
                    "match": {"order_id": "1001"},
                },
            ),
        )

        result = await PlatformEventPublisher(db).publish(
            user_id=first_user_id,
            event_type="shopify.order.updated",
            source="shopify",
            payload={"order_id": "1001"},
        )

        resolved_ids = {
            wait_id
            for handler_result in result["handler_results"]
            for wait_id in handler_result.get("resolved_wait_ids", [])
        }

        assert str(first_wait.id) in resolved_ids
        assert str(second_wait.id) not in resolved_ids

        first_saved = await WorkflowWaitService(db).get_for_user(
            user_id=first_user_id,
            wait_id=first_wait.id,
        )
        second_saved = await WorkflowWaitService(db).get_for_user(
            user_id=second_user_id,
            wait_id=second_wait.id,
        )

        assert first_saved.status == "resolved"
        assert second_saved.status == "waiting"

        break
