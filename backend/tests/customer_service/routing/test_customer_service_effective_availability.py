from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import get_db
from app.domains.customer_service.models import CustomerServiceAgent, CustomerServiceAgentTimeOff
from app.domains.customer_service.services.workforce.availability import AgentAvailabilityService


@pytest.mark.asyncio
async def test_scheduled_agent_is_only_eligible_during_its_shift():
    workspace_id = uuid4()
    agent = CustomerServiceAgent(
        user_id=workspace_id, agent_user_id=uuid4(), display_name="Scheduled",
        availability="available", availability_mode="scheduled",
        schedule_timezone="America/New_York",
        weekly_schedule={"mon": [{"start": "09:00", "end": "17:00"}]},
    )
    async for db in get_db():
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        service = AgentAvailabilityService(db)
        assert (await service.evaluate(agent=agent, now=datetime(2026, 1, 5, 15, tzinfo=timezone.utc)))["routing_eligible"]
        after = await service.evaluate(agent=agent, now=datetime(2026, 1, 5, 23, tzinfo=timezone.utc))
        assert after["routing_eligible"] is False
        assert after["effective_availability"] == "off_shift"
        await db.delete(agent)
        await db.commit()
        break


@pytest.mark.asyncio
async def test_time_off_overrides_available_on_shift_agent():
    workspace_id = uuid4()
    now = datetime.now(timezone.utc)
    agent = CustomerServiceAgent(
        user_id=workspace_id, agent_user_id=uuid4(), display_name="Away",
        availability="available", availability_mode="manual",
    )
    async for db in get_db():
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        row = CustomerServiceAgentTimeOff(
            workspace_id=workspace_id, agent_id=agent.id,
            starts_at=now - timedelta(minutes=5), ends_at=now + timedelta(minutes=5),
        )
        db.add(row)
        await db.commit()
        result = await AgentAvailabilityService(db).evaluate(agent=agent, now=now)
        assert result["time_off"] is True
        assert result["routing_eligible"] is False
        assert result["effective_availability"] == "time_off"
        await db.delete(agent)
        await db.commit()
        break
