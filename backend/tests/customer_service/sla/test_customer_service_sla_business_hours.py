from datetime import datetime, timezone

from app.domains.customer_service.services.sla import add_business_minutes


def test_add_business_minutes_keeps_legacy_24_7_behavior_without_calendar():
    start = datetime(2026, 6, 15, 16, 30, tzinfo=timezone.utc)

    due = add_business_minutes(start, 60, None)

    assert due == datetime(2026, 6, 15, 17, 30, tzinfo=timezone.utc)


def test_add_business_minutes_rolls_over_to_next_business_window():
    start = datetime(2026, 6, 15, 16, 30, tzinfo=timezone.utc)  # Monday
    calendar = {
        "timezone": "UTC",
        "weekly_hours": {
            "mon": [{"start": "09:00", "end": "17:00"}],
            "tue": [{"start": "09:00", "end": "17:00"}],
            "wed": [{"start": "09:00", "end": "17:00"}],
            "thu": [{"start": "09:00", "end": "17:00"}],
            "fri": [{"start": "09:00", "end": "17:00"}],
        },
    }

    due = add_business_minutes(start, 60, calendar)

    assert due == datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc)
