from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import CustomerServiceMacro
from app.domains.customer_service.schemas.macros import MacroCreate, MacroUpdate


class MacroRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, *, user_id, payload: MacroCreate):
        macro = CustomerServiceMacro(user_id=user_id, **payload.model_dump())
        self.db.add(macro)
        await self.db.commit()
        await self.db.refresh(macro)
        return macro

    async def list(self, *, user_id, active_only: bool = True):
        stmt = select(CustomerServiceMacro).where(
            CustomerServiceMacro.user_id == user_id
        )
        if active_only:
            stmt = stmt.where(CustomerServiceMacro.is_active.is_(True))
        stmt = stmt.order_by(CustomerServiceMacro.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get(self, *, user_id, macro_id):
        result = await self.db.execute(
            select(CustomerServiceMacro).where(
                CustomerServiceMacro.user_id == user_id,
                CustomerServiceMacro.id == macro_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, *, user_id, macro_id, payload: MacroUpdate):
        macro = await self.get(user_id=user_id, macro_id=macro_id)
        if macro is None:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(macro, key, value)
        await self.db.commit()
        await self.db.refresh(macro)
        return macro
