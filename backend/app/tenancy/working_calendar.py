"""Small, workspace-owned working-calendar primitive.

All instants remain UTC at persistence boundaries; this module only interprets
them in a workspace's IANA timezone.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
OPERATING_MODES = {"scheduled", "24_7", "closed_ai_only"}
MAX_WINDOWS_PER_DAY = 8

DEFAULT_WORKING_CALENDAR: dict[str, Any] = {
    "mode": "24_7",
    "weekly_hours": {},
    "holidays": [],
    "out_of_hours": {
        "widget_state": "away",
        "auto_reply_enabled": False,
        "auto_reply_text": None,
    },
}


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("timezone must be a valid IANA timezone") from exc
    return value


def _parse_hhmm(value: str) -> time:
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        raise ValueError("business-hour times must use HH:MM")
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("business-hour times must use HH:MM") from exc
    if parsed.second or parsed.microsecond:
        raise ValueError("business-hour times must use HH:MM")
    return parsed


def normalize_working_calendar(value: dict[str, Any] | None) -> dict[str, Any]:
    """Validate and normalize the durable workspace calendar JSON shape."""
    if value is None:
        return {**DEFAULT_WORKING_CALENDAR, "weekly_hours": {}, "holidays": [],
                "out_of_hours": dict(DEFAULT_WORKING_CALENDAR["out_of_hours"])}
    if not isinstance(value, dict):
        raise ValueError("business_hours must be an object")
    allowed = {"mode", "weekly_hours", "holidays", "out_of_hours"}
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"unknown business_hours fields: {', '.join(sorted(unknown))}")
    mode = value.get("mode", "scheduled")
    if mode not in OPERATING_MODES:
        raise ValueError("business_hours.mode must be scheduled, 24_7, or closed_ai_only")

    weekly = value.get("weekly_hours", {})
    if not isinstance(weekly, dict) or set(weekly) - set(WEEKDAY_KEYS):
        raise ValueError("weekly_hours contains an unknown day key")
    normalized_weekly: dict[str, list[dict[str, str]]] = {}
    for day, windows in weekly.items():
        if not isinstance(windows, list) or len(windows) > MAX_WINDOWS_PER_DAY:
            raise ValueError("each day must have a reasonable list of windows")
        parsed_windows: list[tuple[time, time]] = []
        for window in windows:
            if not isinstance(window, dict) or set(window) != {"start", "end"}:
                raise ValueError("each window requires start and end")
            start, end = _parse_hhmm(window["start"]), _parse_hhmm(window["end"])
            if start >= end:
                raise ValueError("business-hour window end must be after start")
            parsed_windows.append((start, end))
        parsed_windows.sort()
        if any(end > next_start for (_, end), (next_start, _) in zip(parsed_windows, parsed_windows[1:])):
            raise ValueError("business-hour windows may not overlap")
        normalized_weekly[day] = [
            {"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M")}
            for start, end in parsed_windows
        ]

    holidays = value.get("holidays", [])
    if not isinstance(holidays, list):
        raise ValueError("holidays must be a list")
    normalized_holidays = []
    seen_dates: set[str] = set()
    for holiday in holidays:
        if not isinstance(holiday, dict) or set(holiday) - {"date", "name"} or "date" not in holiday:
            raise ValueError("each holiday requires date and optional name")
        raw_date = holiday["date"]
        if not isinstance(raw_date, str):
            raise ValueError("holiday date must be ISO YYYY-MM-DD")
        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ValueError("holiday date must be ISO YYYY-MM-DD") from exc
        normalized_date = parsed_date.isoformat()
        if normalized_date in seen_dates:
            raise ValueError("holiday dates must be unique")
        seen_dates.add(normalized_date)
        name = holiday.get("name")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("holiday name must be non-empty when provided")
        item = {"date": normalized_date}
        if name is not None:
            item["name"] = name.strip()
        normalized_holidays.append(item)

    out = value.get("out_of_hours", {})
    if not isinstance(out, dict) or set(out) - {"widget_state", "auto_reply_enabled", "auto_reply_text"}:
        raise ValueError("out_of_hours has unsupported fields")
    widget_state = out.get("widget_state", "away")
    if widget_state != "away":
        raise ValueError("out_of_hours.widget_state must be away")
    enabled = out.get("auto_reply_enabled", False)
    text = out.get("auto_reply_text")
    if not isinstance(enabled, bool) or (text is not None and not isinstance(text, str)):
        raise ValueError("out_of_hours auto-reply configuration is invalid")
    if enabled and not (text and text.strip()):
        raise ValueError("auto_reply_text is required when auto_reply_enabled")
    return {
        "mode": mode,
        "weekly_hours": normalized_weekly,
        "holidays": normalized_holidays,
        "out_of_hours": {"widget_state": widget_state, "auto_reply_enabled": enabled,
                           "auto_reply_text": text.strip() if isinstance(text, str) else None},
    }


def resolved_workspace_calendar(*, timezone_name: str | None, business_hours: dict | None) -> dict[str, Any]:
    calendar = normalize_working_calendar(business_hours)
    return {**calendar, "timezone": validate_timezone(timezone_name or "UTC")}


def is_working_time(at: datetime, calendar: dict[str, Any]) -> bool:
    if calendar["mode"] == "24_7":
        return True
    if calendar["mode"] == "closed_ai_only":
        return False
    local = at.astimezone(ZoneInfo(calendar["timezone"]))
    if local.date().isoformat() in {item["date"] for item in calendar["holidays"]}:
        return False
    current = local.timetz().replace(tzinfo=None)
    return any(_parse_hhmm(w["start"]) <= current < _parse_hhmm(w["end"])
               for w in calendar["weekly_hours"].get(WEEKDAY_KEYS[local.weekday()], []))


def operating_state(at: datetime, calendar: dict[str, Any]) -> str:
    if calendar["mode"] == "closed_ai_only":
        return "ai_only"
    return "open" if is_working_time(at, calendar) else "away"


def add_working_minutes(start_at: datetime, minutes: int, calendar: dict[str, Any] | None) -> datetime:
    if not calendar or calendar.get("mode") == "24_7":
        return start_at + timedelta(minutes=minutes)
    if calendar.get("mode") == "closed_ai_only":
        raise ValueError("cannot calculate an SLA due date for a closed_ai_only calendar")
    # SLA policy business_hours predates workspace calendars and may omit a
    # timezone. Retain its documented UTC fallback while new workspace
    # calendars always inject their validated IANA timezone.
    tz = ZoneInfo(calendar.get("timezone") or "UTC")
    remaining, current = timedelta(minutes=minutes), start_at.astimezone(tz)
    holiday_dates = {item["date"] if isinstance(item, dict) else item for item in calendar.get("holidays", [])}
    for _ in range(370):
        windows = [] if current.date().isoformat() in holiday_dates else calendar.get("weekly_hours", {}).get(WEEKDAY_KEYS[current.weekday()], [])
        for window in windows:
            window_start = datetime.combine(current.date(), _parse_hhmm(window["start"]), tzinfo=tz)
            window_end = datetime.combine(current.date(), _parse_hhmm(window["end"]), tzinfo=tz)
            if current < window_start:
                current = window_start
            if current >= window_end:
                continue
            available = window_end - current
            if remaining <= available:
                return (current + remaining).astimezone(start_at.tzinfo or timezone.utc)
            remaining -= available
            current = window_end
        current = datetime.combine(current.date() + timedelta(days=1), time.min, tzinfo=tz)
    raise ValueError("Unable to calculate SLA due date from business_hours")
