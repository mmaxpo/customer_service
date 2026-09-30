from sqlalchemy import select, or_

from app.domains.customer_service.models import CustomerServiceWorkflowTemplate


class WorkflowTemplateRepository:
    def __init__(self, db):

        self.db = db

    async def create(self, **kwargs):

        obj = CustomerServiceWorkflowTemplate(**kwargs)

        self.db.add(obj)

        await self.db.commit()

        await self.db.refresh(obj)

        return obj

    async def list(self, user_id):

        result = await self.db.execute(
            select(CustomerServiceWorkflowTemplate).where(
                or_(
                    CustomerServiceWorkflowTemplate.scope == "system",
                    CustomerServiceWorkflowTemplate.user_id == user_id,
                )
            )
        )

        return result.scalars().all()

    async def get_system_by_name(
        self,
        *,
        category,
        name,
    ):

        result = await self.db.execute(
            select(CustomerServiceWorkflowTemplate).where(
                CustomerServiceWorkflowTemplate.scope == "system",
                CustomerServiceWorkflowTemplate.category == category,
                CustomerServiceWorkflowTemplate.name == name,
            )
        )

        return result.scalar_one_or_none()

    async def get_for_user(
        self,
        *,
        user_id,
        template_id,
    ):

        result = await self.db.execute(
            select(CustomerServiceWorkflowTemplate).where(
                CustomerServiceWorkflowTemplate.id == template_id,
                or_(
                    CustomerServiceWorkflowTemplate.scope == "system",
                    CustomerServiceWorkflowTemplate.user_id == user_id,
                ),
            )
        )

        return result.scalar_one_or_none()

    async def update(
        self,
        *,
        template,
        values,
    ):

        for key, value in values.items():
            setattr(template, key, value)

        await self.db.commit()
        await self.db.refresh(template)

        return template
