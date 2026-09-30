from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db

router = APIRouter()


@router.get("")
def health():
    return {"status": "ok"}


@router.get("/live")
def liveness():
    return {"status": "alive"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    expected_head = ScriptDirectory.from_config(
        Config("alembic.ini")
    ).get_current_head()
    try:
        await db.execute(text("SELECT 1"))
        current_head = await db.scalar(text("SELECT version_num FROM alembic_version"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    if current_head != expected_head:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "database_migration_required",
                "current": current_head,
                "expected": expected_head,
            },
        )
    return {"status": "ready", "database_revision": current_head}
