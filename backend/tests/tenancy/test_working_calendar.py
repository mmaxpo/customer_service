from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.tenancy.schemas import WorkspaceCreate, WorkspaceUpdate
from app.tenancy.working_calendar import (
    add_working_minutes,
    is_working_time,
    operating_state,
    resolved_workspace_calendar,
)


def _scheduled(*, holidays=None):
    return resolved_workspace_calendar(
        timezone_name="America/New_York",
        business_hours={
            "mode": "scheduled",
            "weekly_hours": {
                "mon": [{"start": "09:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}],
                "tue": [{"start": "09:00", "end": "17:00"}],
                "wed": [{"start": "09:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}],
                "fri": [{"start": "09:00", "end": "17:00"}],
            },
            "holidays": holidays or [],
            "out_of_hours": {"widget_state": "away", "auto_reply_enabled": False, "auto_reply_text": None},
        },
    )


def test_workspace_timezone_accepts_iana_zones_and_rejects_offsets():
    for zone in ("America/New_York", "Europe/London", "Asia/Tehran", "UTC"):
        assert WorkspaceCreate(name="Calendar", timezone=zone).timezone == zone
    with pytest.raises(ValidationError):
        WorkspaceUpdate(timezone="UTC-5")


@pytest.mark.parametrize(
    "calendar",
    [
        {"mode": "scheduled", "weekly_hours": {"noday": []}},
        {"mode": "scheduled", "weekly_hours": {"mon": [{"start": "9:00", "end": "17:00"}]}},
        {"mode": "scheduled", "weekly_hours": {"mon": [{"start": "17:00", "end": "09:00"}]}},
        {"mode": "scheduled", "weekly_hours": {"mon": [{"start": "09:00", "end": "12:00"}, {"start": "11:00", "end": "17:00"}]}},
    ],
)
def test_workspace_schedule_rejects_invalid_windows(calendar):
    with pytest.raises(ValidationError):
        WorkspaceUpdate(business_hours=calendar)


def test_scheduled_holiday_and_multiple_windows_control_availability():
    calendar = _scheduled(holidays=[{"date": "2026-06-15", "name": "Closed"}])
    assert not is_working_time(datetime(2026, 6, 15, 15, tzinfo=timezone.utc), calendar)
    assert is_working_time(datetime(2026, 6, 16, 15, tzinfo=timezone.utc), calendar)
    assert not is_working_time(datetime(2026, 6, 17, 16, 30, tzinfo=timezone.utc), calendar)  # lunch


def test_modes_and_dst_working_minutes_are_explicit():
    around_dst = datetime(2026, 3, 6, 21, 30, tzinfo=timezone.utc)  # Fri 16:30 EST
    calendar = _scheduled()
    # The weekend contains the New York DST change; next Tuesday 09:30 is EDT.
    assert add_working_minutes(around_dst, 60, calendar) == datetime(2026, 3, 9, 13, 30, tzinfo=timezone.utc)
    always = resolved_workspace_calendar(timezone_name="UTC", business_hours={"mode": "24_7"})
    ai_only = resolved_workspace_calendar(timezone_name="UTC", business_hours={"mode": "closed_ai_only"})
    assert operating_state(around_dst, always) == "open"
    assert operating_state(around_dst, ai_only) == "ai_only"
    assert not is_working_time(around_dst, ai_only)


def test_holidays_are_editable_through_the_audited_workspace_patch_shape():
    initial = WorkspaceUpdate(business_hours={
        "mode": "scheduled", "weekly_hours": _scheduled()["weekly_hours"], "holidays": [],
    })
    # The actual public contract replaces the complete validated calendar,
    # making add/edit/delete deterministic without a second persistence API.
    updated = WorkspaceUpdate(business_hours={
        "mode": "scheduled", "weekly_hours": initial.business_hours["weekly_hours"],
        "holidays": [{"date": "2026-12-25", "name": "Holiday"}],
    })
    deleted = WorkspaceUpdate(business_hours={
        "mode": "scheduled", "weekly_hours": updated.business_hours["weekly_hours"], "holidays": [],
    })
    assert updated.business_hours["holidays"][0]["name"] == "Holiday"
    assert deleted.business_hours["holidays"] == []
