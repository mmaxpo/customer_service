from datetime import datetime, timedelta, timezone

DEFAULT_LEASE_SECONDS = 300


def lease_expires_at(
    *,
    now: datetime | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now + timedelta(seconds=lease_seconds)


def is_lease_expired(
    *,
    locked_at: datetime | None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
) -> bool:
    if locked_at is None:
        return True

    now = now or datetime.now(timezone.utc)

    if locked_at.tzinfo is None:
        locked_at = locked_at.replace(tzinfo=timezone.utc)

    return locked_at + timedelta(seconds=lease_seconds) <= now
