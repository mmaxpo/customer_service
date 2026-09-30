from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import CustomerServiceAgent, CustomerServiceAgentTimeOff
from app.core.config import settings

AUTO_AWAY_MINUTES = settings.AGENT_AUTO_AWAY_MINUTES


class AgentAvailabilityService:
    """Single routing/UI decision point for workforce availability."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(self, *, agent: CustomerServiceAgent, now: datetime | None = None,
                       online: bool | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        on_shift = await self.on_shift(agent=agent, now=now)
        time_off = await self.is_on_time_off(agent=agent, now=now)
        presence = agent.availability
        source = getattr(agent, "availability_source", "manual") or "manual"
        if presence == "available" and agent.last_activity_at:
            age = (now - _aware(agent.last_activity_at)).total_seconds()
            if age >= AUTO_AWAY_MINUTES * 60:
                presence = "away"
        if online is False:
            presence = "offline"
        eligible = (
            agent.status == "active"
            and not time_off
            and presence == "available"
            and (agent.availability_mode != "scheduled" or on_shift is True)
        )
        return {
            "presence": presence,
            "effective_availability": presence if eligible else self._reason(presence, on_shift, time_off),
            "availability_mode": agent.availability_mode or "manual",
            "on_shift": on_shift,
            "time_off": time_off,
            "routing_eligible": eligible,
            "availability_source": source,
        }

    async def on_shift(self, *, agent: CustomerServiceAgent, now: datetime) -> bool | None:
        if (agent.availability_mode or "manual") != "scheduled":
            return None
        tz = ZoneInfo(agent.schedule_timezone or "UTC")
        local = now.astimezone(tz)
        days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        intervals = (agent.weekly_schedule or {}).get(days[local.weekday()], [])
        current = local.time()
        for item in intervals:
            try:
                start = time.fromisoformat(item["start"])
                end = time.fromisoformat(item["end"])
            except (KeyError, TypeError, ValueError):
                continue
            if start <= current < end:
                return True
        return False

    async def is_on_time_off(self, *, agent: CustomerServiceAgent, now: datetime) -> bool:
        result = await self.db.execute(
            select(CustomerServiceAgentTimeOff.id).where(
                CustomerServiceAgentTimeOff.workspace_id == agent.user_id,
                CustomerServiceAgentTimeOff.agent_id == agent.id,
                CustomerServiceAgentTimeOff.starts_at <= now,
                CustomerServiceAgentTimeOff.ends_at > now,
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def sweep_auto_away(self, *, now: datetime | None = None) -> int:
        """Transition idle available agents without one delayed job per agent."""
        now = now or datetime.now(timezone.utc)
        rows = (await self.db.scalars(select(CustomerServiceAgent).where(
            CustomerServiceAgent.status == "active",
            CustomerServiceAgent.availability == "available",
            CustomerServiceAgent.last_activity_at.is_not(None),
        ))).all()
        changed = 0
        for agent in rows:
            if (now - _aware(agent.last_activity_at)).total_seconds() >= AUTO_AWAY_MINUTES * 60:
                agent.availability = "away"
                agent.availability_source = "idle"
                changed += 1
        if changed:
            await self.db.commit()
        return changed

    @staticmethod
    def _reason(presence: str, on_shift: bool | None, time_off: bool) -> str:
        if time_off:
            return "time_off"
        if presence != "available":
            return presence
        if on_shift is False:
            return "off_shift"
        return "unavailable"


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
