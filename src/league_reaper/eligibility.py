"""Pure rules deciding which leagues the reaper may remove (backend/league-reaper).

A league is removable once a full calendar year has passed since its latest activity:
``last_accessed_at`` when it has ever been opened, otherwise ``onboarded_at``. Anything
unreadable keeps the league, since removal is permanent.
"""

from datetime import UTC, datetime
from typing import Any


def parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO 8601 timestamp, treating a naive value as UTC.

    Returns:
        The aware datetime, or ``None`` if ``value`` is missing or unparseable.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def add_one_year(moment: datetime) -> datetime:
    """Return the same date one calendar year later (February 29 becomes March 1)."""
    try:
        return moment.replace(year=moment.year + 1)
    except ValueError:
        return moment.replace(year=moment.year + 1, month=3, day=1)


def last_activity(metadata: dict) -> datetime | None:
    """Return when a league was last active, or ``None`` if that can't be determined.

    A ``last_accessed_at`` that is present but unparseable never falls back to
    ``onboarded_at``: the league has been opened, we just can't tell when.
    """
    onboarded = parse_timestamp(metadata.get("onboarded_at"))
    if onboarded is None:
        return None
    if "last_accessed_at" not in metadata:
        return onboarded
    return parse_timestamp(metadata["last_accessed_at"])


def is_expired(metadata: dict, now: datetime) -> bool:
    """Return whether a league has been idle for at least one calendar year."""
    activity = last_activity(metadata)
    return activity is not None and now >= add_one_year(activity)
