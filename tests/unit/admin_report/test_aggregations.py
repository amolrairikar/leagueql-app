"""Tests for the pure aggregation helpers in src/admin_report/aggregations.py."""

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_MODULE = Path(__file__).parents[3] / "src" / "admin_report" / "aggregations.py"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def agg():
    mod = _load_module("admin_report_aggregations", _MODULE)
    yield mod
    sys.modules.pop("admin_report_aggregations", None)


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


# ---- effective_platform -------------------------------------------------------


class TestEffectivePlatform:
    def test_prefers_active_platform(self, agg):
        item = {"platform": "ESPN", "active_platform": "SLEEPER"}
        assert agg.effective_platform(item) == "SLEEPER"

    def test_falls_back_to_platform(self, agg):
        assert agg.effective_platform({"platform": "ESPN"}) == "ESPN"

    def test_none_when_absent(self, agg):
        assert agg.effective_platform({}) is None

    def test_empty_active_platform_falls_back(self, agg):
        item = {"platform": "SLEEPER", "active_platform": ""}
        assert agg.effective_platform(item) == "SLEEPER"


# ---- parse_timestamp ----------------------------------------------------------


class TestParseTimestamp:
    def test_parses_z_suffix_to_utc(self, agg):
        parsed = agg.parse_timestamp("2024-09-01T00:00:00Z")
        assert parsed == _dt("2024-09-01T00:00:00+00:00")
        assert parsed.tzinfo is not None

    def test_naive_assumed_utc(self, agg):
        parsed = agg.parse_timestamp("2024-09-01T00:00:00")
        assert parsed == _dt("2024-09-01T00:00:00+00:00")

    def test_offset_converted_to_utc(self, agg):
        parsed = agg.parse_timestamp("2024-09-01T02:00:00+02:00")
        assert parsed == _dt("2024-09-01T00:00:00+00:00")

    @pytest.mark.parametrize("value", ["not-a-date", "", None, 12345, {}])
    def test_unparseable_or_non_string_is_none(self, agg, value):
        assert agg.parse_timestamp(value) is None


# ---- count_total --------------------------------------------------------------


class TestCountTotal:
    def test_empty(self, agg):
        assert agg.count_total([]) == 0

    def test_counts_only_parseable_onboarded_at(self, agg):
        items = [
            {"onboarded_at": "2024-01-01T00:00:00Z"},
            {"onboarded_at": "2024-02-01T00:00:00Z"},
            {"onboarded_at": "bad"},
            {},
        ]
        assert agg.count_total(items) == 2


# ---- count_active -------------------------------------------------------------


class TestCountActive:
    def test_empty(self, agg):
        assert agg.count_active([], datetime.now(timezone.utc)) == 0

    def test_inside_outside_and_missing_window(self, agg):
        now = _dt("2024-02-01T00:00:00Z")
        items = [
            {"last_accessed_at": "2024-01-25T00:00:00Z"},  # 7d ago -> active
            {"last_accessed_at": "2024-01-01T00:00:00Z"},  # 31d ago -> inactive
            {"last_accessed_at": "bad"},  # unparseable -> inactive
            {},  # missing -> inactive
        ]
        assert agg.count_active(items, now, days=14) == 1

    def test_boundary_is_inclusive(self, agg):
        now = _dt("2024-02-01T00:00:00Z")
        # Exactly 14 days before `now` -> counts as active (>= cutoff).
        items = [{"last_accessed_at": "2024-01-18T00:00:00Z"}]
        assert agg.count_active(items, now, days=14) == 1

    def test_custom_days(self, agg):
        now = _dt("2024-02-01T00:00:00Z")
        items = [{"last_accessed_at": "2024-01-05T00:00:00Z"}]  # 27d ago
        assert agg.count_active(items, now, days=14) == 0
        assert agg.count_active(items, now, days=30) == 1


# ---- platform_counts ----------------------------------------------------------


class TestPlatformCounts:
    def test_empty_has_zero_defaults(self, agg):
        assert agg.platform_counts([]) == {"ESPN": 0, "SLEEPER": 0}

    def test_counts_split_with_migration(self, agg):
        items = [
            {"platform": "ESPN"},
            {"platform": "ESPN"},
            {"platform": "SLEEPER"},
            {"platform": "ESPN", "active_platform": "SLEEPER"},  # migrated -> SLEEPER
        ]
        assert agg.platform_counts(items) == {"ESPN": 2, "SLEEPER": 2}

    def test_none_or_unknown_platform_ignored(self, agg):
        items = [
            {},  # no platform -> None
            {"platform": "YAHOO"},  # unknown -> ignored
            {"platform": "SLEEPER"},
        ]
        assert agg.platform_counts(items) == {"ESPN": 0, "SLEEPER": 1}


# ---- new_onboards -------------------------------------------------------------


class TestNewOnboards:
    def test_empty(self, agg):
        assert agg.new_onboards([], datetime.now(timezone.utc)) == {
            "24h": 0,
            "7d": 0,
            "30d": 0,
        }

    def test_windows_are_cumulative(self, agg):
        now = _dt("2024-02-01T00:00:00Z")
        items = [
            {"onboarded_at": "2024-01-31T12:00:00Z"},  # 12h ago -> all windows
            {"onboarded_at": "2024-01-28T00:00:00Z"},  # 4d ago -> 7d + 30d
            {"onboarded_at": "2024-01-10T00:00:00Z"},  # 22d ago -> 30d only
            {"onboarded_at": "2023-12-01T00:00:00Z"},  # 62d ago -> none
        ]
        assert agg.new_onboards(items, now) == {"24h": 1, "7d": 2, "30d": 3}

    def test_boundaries_inclusive(self, agg):
        now = _dt("2024-02-01T00:00:00Z")
        items = [
            {"onboarded_at": "2024-01-31T00:00:00Z"},  # exactly 24h -> counted
            {"onboarded_at": "2024-01-25T00:00:00Z"},  # exactly 7d -> counted
            {"onboarded_at": "2024-01-02T00:00:00Z"},  # exactly 30d -> counted
        ]
        assert agg.new_onboards(items, now) == {"24h": 1, "7d": 2, "30d": 3}

    def test_missing_or_unparseable_excluded(self, agg):
        now = _dt("2024-02-01T00:00:00Z")
        items = [
            {"onboarded_at": "bad"},
            {},
            {"onboarded_at": "2024-01-31T12:00:00Z"},  # valid, recent
        ]
        assert agg.new_onboards(items, now) == {"24h": 1, "7d": 1, "30d": 1}
