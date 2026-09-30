from fastapi import HTTPException
from app.runtime.validation import validate_workflow
from app.domains.customer_service.services.shopify_workflow_catalog import (
    shopify_system_workflow_templates,
)
from app.domains.customer_service.services.chatbot_workflow_catalog import (
    website_chat_system_workflow_templates,
)
from app.domains.customer_service.repositories.workflow_templates import (
    WorkflowTemplateRepository,
)


def _raise_if_invalid_workflow(workflow_json: dict | None) -> None:
    if not workflow_json:
        raise HTTPException(status_code=400, detail="workflow_json is required")

    errors = validate_workflow(workflow_json, strict=True)
    if errors:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_workflow_template",
                "errors": [
                    {
                        "code": getattr(error, "code", None),
                        "message": getattr(error, "message", str(error)),
                        "details": getattr(error, "details", None),
                    }
                    for error in errors
                ],
            },
        )


class WorkflowTemplateService:
    def __init__(self, db):

        self.db = db

        self.repo = WorkflowTemplateRepository(db)

    async def create(self, user_id, payload):

        _raise_if_invalid_workflow(payload.workflow_json)

        return await self.repo.create(
            user_id=user_id,
            category=payload.category,
            name=payload.name,
            description=payload.description,
            workflow_json=payload.workflow_json,
            input_schema=payload.input_schema,
            output_schema=payload.output_schema,
            tags=payload.tags,
            scope="private",
            status="draft",
        )

    async def list(self, user_id):

        return await self.repo.list(user_id)

    async def seed_shopify_system_templates(self):

        created = []
        existing = []

        for template in shopify_system_workflow_templates():
            _raise_if_invalid_workflow(template["workflow_json"])

            current = await self.repo.get_system_by_name(
                category=template["category"],
                name=template["name"],
            )

            if current is not None:
                updated = await self.repo.update(
                    template=current,
                    values={
                        "description": template.get("description"),
                        "workflow_json": template["workflow_json"],
                        "input_schema": template.get("input_schema"),
                        "output_schema": template.get("output_schema"),
                        "tags": template.get("tags"),
                        "version": template.get("version", "1.0.0"),
                        "status": "published",
                    },
                )
                existing.append(updated)
                continue

            created.append(
                await self.repo.create(
                    user_id=None,
                    scope="system",
                    status="published",
                    category=template["category"],
                    name=template["name"],
                    description=template.get("description"),
                    workflow_json=template["workflow_json"],
                    input_schema=template.get("input_schema"),
                    output_schema=template.get("output_schema"),
                    tags=template.get("tags"),
                    version=template.get("version", "1.0.0"),
                )
            )

        return {
            "created": created,
            "existing": existing,
            "created_count": len(created),
            "existing_count": len(existing),
        }

    async def seed_website_chat_system_templates(self):

        created = []
        existing = []

        for template in website_chat_system_workflow_templates():
            _raise_if_invalid_workflow(template["workflow_json"])

            current = await self.repo.get_system_by_name(
                category=template["category"],
                name=template["name"],
            )

            if current is not None:
                updated = await self.repo.update(
                    template=current,
                    values={
                        "description": template.get("description"),
                        "workflow_json": template["workflow_json"],
                        "input_schema": template.get("input_schema"),
                        "output_schema": template.get("output_schema"),
                        "tags": template.get("tags"),
                        "version": template.get("version", "1.0.0"),
                        "status": "published",
                    },
                )
                existing.append(updated)
                continue

            created.append(
                await self.repo.create(
                    user_id=None,
                    scope="system",
                    status="published",
                    category=template["category"],
                    name=template["name"],
                    description=template.get("description"),
                    workflow_json=template["workflow_json"],
                    input_schema=template.get("input_schema"),
                    output_schema=template.get("output_schema"),
                    tags=template.get("tags"),
                    version=template.get("version", "1.0.0"),
                )
            )

        return {
            "created": created,
            "existing": existing,
            "created_count": len(created),
            "existing_count": len(existing),
        }

    async def clone(
        self,
        *,
        user_id,
        template_id,
        payload,
    ):

        source = await self.repo.get_for_user(
            user_id=user_id,
            template_id=template_id,
        )

        if source is None:
            raise HTTPException(
                status_code=404,
                detail="Workflow template not found",
            )

        clone_name = payload.name or f"{source.name} Copy"
        clone_description = (
            payload.description
            if payload.description is not None
            else source.description
        )

        workflow_json = dict(source.workflow_json or {})
        workflow_json["name"] = clone_name
        _raise_if_invalid_workflow(workflow_json)

        return await self.repo.create(
            user_id=user_id,
            scope="private",
            status="draft",
            category=source.category,
            name=clone_name,
            description=clone_description,
            workflow_json=workflow_json,
            input_schema=source.input_schema,
            output_schema=source.output_schema,
            tags=source.tags,
            version=source.version,
        )

    async def update(
        self,
        *,
        user_id,
        template_id,
        payload,
    ):

        template = await self.repo.get_for_user(
            user_id=user_id,
            template_id=template_id,
        )

        if template is None:
            raise HTTPException(
                status_code=404,
                detail="Workflow template not found",
            )

        if template.scope != "private" or template.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Only private workflow templates can be edited",
            )

        if template.status != "draft":
            raise HTTPException(
                status_code=409,
                detail="Only draft workflow templates can be edited",
            )

        values = payload.model_dump(exclude_unset=True)

        if "workflow_json" in values:
            _raise_if_invalid_workflow(values["workflow_json"])

        return await self.repo.update(
            template=template,
            values=values,
        )

    async def publish(
        self,
        *,
        user_id,
        template_id,
    ):

        template = await self.repo.get_for_user(
            user_id=user_id,
            template_id=template_id,
        )

        if template is None:
            raise HTTPException(
                status_code=404,
                detail="Workflow template not found",
            )

        if template.scope != "private" or template.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Only private workflow templates can be published",
            )

        _raise_if_invalid_workflow(template.workflow_json)

        return await self.repo.update(
            template=template,
            values={"status": "published"},
        )

    async def unpublish(
        self,
        *,
        user_id,
        template_id,
    ):

        template = await self.repo.get_for_user(
            user_id=user_id,
            template_id=template_id,
        )

        if template is None:
            raise HTTPException(
                status_code=404,
                detail="Workflow template not found",
            )

        if template.scope != "private" or template.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Only private workflow templates can be unpublished",
            )

        return await self.repo.update(
            template=template,
            values={"status": "draft"},
        )
