"""Pure data-aggregation helpers for the LeagueQL admin dashboard.

These functions contain no boto3 / Streamlit / I/O so they can be unit-tested in
isolation. They operate on the ``METADATA`` items returned by a GSI3 query
(partition key ``SK = "METADATA"``), whose relevant attributes are:

  * ``platform``          — enum ``ESPN`` / ``SLEEPER`` (the onboarding platform)
  * ``active_platform``   — enum, present only after an ESPN->Sleeper migration;
                            when set it is the authoritative current platform
  * ``onboarded_at``      — ISO 8601 (UTC) onboard timestamp (GSI3 sort key)
  * ``last_accessed_at``  — ISO 8601 (UTC) last-opened timestamp; absent on older
                            leagues and any never opened since the field shipped

See ``docs/db/dynamodb_spec.md`` (METADATA item + GSI3).
"""

import pandas as pd

_DEFAULT_ACTIVE_DAYS = 14
_PLATFORMS = ("ESPN", "SLEEPER")


def effective_platform(item: dict) -> str | None:
    """Authoritative current platform for a METADATA item.

    ``active_platform`` (set on migrated leagues) wins over the original
    ``platform``; returns ``None`` if neither is present.
    """
    return item.get("active_platform") or item.get("platform")


def build_dataframe(items: list[dict]) -> pd.DataFrame:
    """Build a normalized DataFrame from raw GSI3 METADATA items.

    Columns: ``platform`` (effective), ``onboarded_at`` and ``last_accessed_at``
    parsed to tz-aware UTC datetimes (unparseable/absent -> ``NaT``).
    """
    records = [
        {
            "platform": effective_platform(item),
            "onboarded_at": item.get("onboarded_at"),
            "last_accessed_at": item.get("last_accessed_at"),
        }
        for item in items
    ]
    df = pd.DataFrame(records, columns=["platform", "onboarded_at", "last_accessed_at"])
    df["onboarded_at"] = pd.to_datetime(df["onboarded_at"], utc=True, errors="coerce")
    df["last_accessed_at"] = pd.to_datetime(
        df["last_accessed_at"], utc=True, errors="coerce"
    )
    return df


def count_active(
    df: pd.DataFrame, now: pd.Timestamp, days: int = _DEFAULT_ACTIVE_DAYS
) -> int:
    """Count leagues accessed within the last ``days`` days.

    A missing ``last_accessed_at`` (``NaT``) counts as inactive.
    """
    if df.empty:
        return 0
    cutoff = now - pd.Timedelta(days=days)
    return int((df["last_accessed_at"] >= cutoff).sum())


def platform_counts(df: pd.DataFrame) -> dict[str, int]:
    """Count leagues per platform, always including ESPN and SLEEPER keys."""
    counts = {platform: 0 for platform in _PLATFORMS}
    if df.empty:
        return counts
    for platform, count in df["platform"].value_counts().items():
        if platform is None:
            continue
        counts[platform] = int(count)
    return counts


def cumulative_series(df: pd.DataFrame) -> pd.DataFrame:
    """Onboard-ordered running total for the cumulative line chart.

    Returns a DataFrame with ``onboarded_at`` (ascending) and a 1-based
    ``cumulative_count``; rows with no ``onboarded_at`` are dropped.
    """
    if df.empty:
        return pd.DataFrame(columns=["onboarded_at", "cumulative_count"])
    ordered = (
        df.dropna(subset=["onboarded_at"])
        .sort_values("onboarded_at")
        .reset_index(drop=True)
    )
    ordered = ordered[["onboarded_at"]].copy()
    ordered["cumulative_count"] = range(1, len(ordered) + 1)
    return ordered
