from uuid import uuid4

import pytest

from app.core.session import get_db
from app.workflow_operations.evaluations.dataset_schemas import (
    WorkflowEvalCaseCreate,
    WorkflowEvalDatasetCreate,
)
from app.workflow_operations.evaluations.dataset_service import (
    WorkflowEvalDatasetService,
)


@pytest.mark.asyncio
async def test_create_list_get_workflow_eval_dataset_with_cases():
    user_id = uuid4()

    async for db in get_db():
        service = WorkflowEvalDatasetService(db)

        dataset = await service.create(
            user_id=user_id,
            payload=WorkflowEvalDatasetCreate(
                name="Customer service refund dataset",
                description="Refund and damaged item evaluation cases",
                domain="customer_service",
                metadata_json={"source": "test"},
                cases=[
                    WorkflowEvalCaseCreate(
                        name="damaged item refund",
                        input_payload={
                            "message": "My item arrived damaged and I want a refund",
                        },
                        expected_output={
                            "answer": "refund_started",
                        },
                        expected_status="ok",
                        tags=["refund", "damaged_item"],
                        priority="high",
                        metadata_json={"difficulty": "easy"},
                    ),
                    WorkflowEvalCaseCreate(
                        name="shipping delay",
                        input_payload={
                            "message": "Where is my package?",
                        },
                        expected_output={
                            "answer": "shipping_lookup",
                        },
                        expected_status="ok",
                        tags=["shipping"],
                        priority="medium",
                    ),
                ],
            ),
        )

        assert dataset.id is not None
        assert dataset.user_id == user_id
        assert dataset.name == "Customer service refund dataset"
        assert dataset.domain == "customer_service"
        assert len(dataset.cases) == 2

        listed = await service.list_for_user(user_id=user_id)

        assert any(item.id == dataset.id for item in listed)

        loaded = await service.get(dataset_id=dataset.id)

        assert loaded is not None
        assert loaded.id == dataset.id
        assert loaded.name == dataset.name
        assert len(loaded.cases) == 2

        case_names = {case.name for case in loaded.cases}

        assert "damaged item refund" in case_names
        assert "shipping delay" in case_names

        first_case = next(
            case for case in loaded.cases if case.name == "damaged item refund"
        )

        assert first_case.input_payload["message"].startswith("My item arrived")
        assert first_case.expected_output["answer"] == "refund_started"
        assert first_case.expected_status == "ok"
        assert "refund" in first_case.tags
        assert first_case.priority == "high"

        break


@pytest.mark.asyncio
async def test_delete_workflow_eval_dataset_cascades_cases():
    user_id = uuid4()

    async for db in get_db():
        service = WorkflowEvalDatasetService(db)

        dataset = await service.create(
            user_id=user_id,
            payload=WorkflowEvalDatasetCreate(
                name="Delete me",
                domain="customer_service",
                cases=[
                    WorkflowEvalCaseCreate(
                        name="case one",
                        input_payload={"message": "hello"},
                        expected_output={"answer": "world"},
                        expected_status="ok",
                    )
                ],
            ),
        )

        loaded = await service.get(dataset_id=dataset.id)

        assert loaded is not None
        assert len(loaded.cases) == 1

        await service.repo.delete(dataset=loaded)

        deleted = await service.get(dataset_id=dataset.id)

        assert deleted is None

        break
