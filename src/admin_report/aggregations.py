"""Pure onboarding-health aggregation helpers for the nightly admin report.

These functions contain no boto3 / HTTP / I/O so they can be unit-tested in isolation.
They operate on the ``METADATA`` items returned by a GSI3 query (partition key
``SK = "METADATA"``), read via the DynamoDB resource ``Table`` interface (native Python
dicts). The relevant attributes are:

  * ``platform``          — enum ``ESPN`` / ``SLEEPER`` (the onboarding platform)
  * ``active_platform``   — enum, present only after an ESPN->Sleeper migration; when set
                            it is the authoritative current platform
  * ``onboarded_at``      — ISO 8601 (UTC) onboard timestamp (GSI3 sort key)
  * ``last_accessed_at``  — ISO 8601 (UTC) last-opened timestamp; absent on older leagues
                            and any never opened since the field shipped

See ``docs/db/dynamodb_spec.md`` (METADATA item + GSI3). This is a pandas-free port of the
former ``scripts/admin_dashboard/aggregations.py`` so it stays light in a Lambda.
"""

from datetime import datetime, timedelta, timezone

_DEFAULT_ACTIVE_DAYS = 14
_PLATFORMS = ("ESPN", "SLEEPER")
# New-onboard windows reported in the digest, in days.
_NEW_ONBOARD_WINDOWS = {"24h": 1, "7d": 7, "30d": 30}


def effective_platform(item: dict) -> str | None:
    """Authoritative current platform for a METADATA item.

    ``active_platform`` (set on migrated leagues) wins over the original ``platform``;
    returns ``None`` if neither is present.
    """
    return item.get("active_platform") or item.get("platform")


def parse_timestamp(value: object) -> datetime | None:
    """Parse an ISO 8601 timestamp to a tz-aware UTC ``datetime``, or ``None``.

    Tolerant replacement for ``pd.to_datetime(..., errors="coerce")``: an absent,
    non-string, or unparseable value yields ``None``; a naive timestamp is assumed UTC.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def count_total(items: list[dict]) -> int:
    """Count leagues with a parseable ``onboarded_at`` (an onboarded league)."""
    return sum(
        1 for item in items if parse_timestamp(item.get("onboarded_at")) is not None
    )


def count_active(
    items: list[dict], now: datetime, days: int = _DEFAULT_ACTIVE_DAYS
) -> int:
    """Count leagues accessed within the last ``days`` days.

    The window is inclusive (``last_accessed_at >= now - days``); a missing or
    unparseable ``last_accessed_at`` counts as inactive.
    """
    cutoff = now - timedelta(days=days)
    count = 0
    for item in items:
        accessed = parse_timestamp(item.get("last_accessed_at"))
        if accessed is not None and accessed >= cutoff:
            count += 1
    return count


def platform_counts(items: list[dict]) -> dict[str, int]:
    """Count leagues per effective platform, always including ESPN and SLEEPER keys."""
    counts = {platform: 0 for platform in _PLATFORMS}
    for item in items:
        platform = effective_platform(item)
        if platform in counts:
            counts[platform] += 1
    return counts


def new_onboards(items: list[dict], now: datetime) -> dict[str, int]:
    """Count leagues onboarded within each trailing window (24h / 7d / 30d).

    Counting is inclusive (``onboarded_at >= now - window``); a missing or unparseable
    ``onboarded_at`` is excluded from every window.
    """
    counts = {label: 0 for label in _NEW_ONBOARD_WINDOWS}
    parsed = [
        ts
        for item in items
        if (ts := parse_timestamp(item.get("onboarded_at"))) is not None
    ]
    for label, days in _NEW_ONBOARD_WINDOWS.items():
        cutoff = now - timedelta(days=days)
        counts[label] = sum(1 for ts in parsed if ts >= cutoff)
    return counts
