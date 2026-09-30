from app.domains.customer_service.models import Customer
from app.domains.customer_service.repositories.customers import CustomerRepository
from app.tenancy.repository import WorkspaceRepository


class CustomerService:
    def __init__(self, db):
        self.db = db
        self.repo = CustomerRepository(db)

    async def create_customer(self, payload, user_id):
        workspace_repo = WorkspaceRepository(self.db)
        workspace = await workspace_repo.get_workspace(user_id)
        if workspace is None:
            workspace = await workspace_repo.get_personal_workspace_for_user(
                user_id=user_id
            )

        customer = Customer(
            user_id=user_id,
            workspace_id=(
                workspace.id if workspace is not None else None
            ),
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            custom_fields=payload.custom_fields,
        )

        return await self.repo.create(customer)

    async def list_customers(self, user_id):
        return await self.repo.list(user_id)

    async def get_customer_summary(self, *, user_id, customer_id):
        return await self.repo.summary(
            user_id=user_id,
            customer_id=customer_id,
        )
