"""Tests for the pure aggregation helpers in scripts/admin_dashboard/aggregations.py."""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

_MODULE = Path(__file__).parents[3] / "scripts" / "admin_dashboard" / "aggregations.py"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def agg():
    mod = _load_module("admin_dashboard_aggregations", _MODULE)
    yield mod
    sys.modules.pop("admin_dashboard_aggregations", None)


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
        # An empty string is falsy, so `platform` should win.
        item = {"platform": "SLEEPER", "active_platform": ""}
        assert agg.effective_platform(item) == "SLEEPER"


# ---- build_dataframe ----------------------------------------------------------


class TestBuildDataframe:
    def test_empty_items(self, agg):
        df = agg.build_dataframe([])
        assert list(df.columns) == ["platform", "onboarded_at", "last_accessed_at"]
        assert df.empty

    def test_parses_timestamps_and_platform(self, agg):
        items = [
            {
                "platform": "ESPN",
                "active_platform": "SLEEPER",
                "onboarded_at": "2024-09-01T00:00:00Z",
                "last_accessed_at": "2024-09-15T00:00:00Z",
            }
        ]
        df = agg.build_dataframe(items)
        assert df.loc[0, "platform"] == "SLEEPER"
        assert df.loc[0, "onboarded_at"] == pd.Timestamp("2024-09-01T00:00:00Z")
        assert df.loc[0, "last_accessed_at"] == pd.Timestamp("2024-09-15T00:00:00Z")

    def test_missing_and_bad_timestamps_become_nat(self, agg):
        items = [
            {"platform": "ESPN", "onboarded_at": "not-a-date"},
            {"platform": "SLEEPER", "onboarded_at": "2024-01-01T00:00:00Z"},
        ]
        df = agg.build_dataframe(items)
        assert pd.isna(df.loc[0, "onboarded_at"])
        assert pd.isna(df.loc[0, "last_accessed_at"])
        assert pd.isna(df.loc[1, "last_accessed_at"])


# ---- count_active -------------------------------------------------------------


class TestCountActive:
    def _df(self, agg, last_accessed):
        items = [
            {"platform": "ESPN", "onboarded_at": "2024-01-01T00:00:00Z", **extra}
            for extra in last_accessed
        ]
        return agg.build_dataframe(items)

    def test_empty(self, agg):
        assert (
            agg.count_active(agg.build_dataframe([]), pd.Timestamp.now(tz="UTC")) == 0
        )

    def test_inside_outside_and_missing_window(self, agg):
        now = pd.Timestamp("2024-02-01T00:00:00Z")
        df = self._df(
            agg,
            [
                {"last_accessed_at": "2024-01-25T00:00:00Z"},  # 7d ago -> active
                {"last_accessed_at": "2024-01-01T00:00:00Z"},  # 31d ago -> inactive
                {},  # missing -> inactive
            ],
        )
        assert agg.count_active(df, now, days=14) == 1

    def test_boundary_is_inclusive(self, agg):
        now = pd.Timestamp("2024-02-01T00:00:00Z")
        # Exactly 14 days before `now` -> counts as active (>= cutoff).
        df = self._df(agg, [{"last_accessed_at": "2024-01-18T00:00:00Z"}])
        assert agg.count_active(df, now, days=14) == 1

    def test_custom_days(self, agg):
        now = pd.Timestamp("2024-02-01T00:00:00Z")
        df = self._df(agg, [{"last_accessed_at": "2024-01-05T00:00:00Z"}])  # 27d ago
        assert agg.count_active(df, now, days=14) == 0
        assert agg.count_active(df, now, days=30) == 1


# ---- platform_counts ----------------------------------------------------------


class TestPlatformCounts:
    def test_empty_has_zero_defaults(self, agg):
        assert agg.platform_counts(agg.build_dataframe([])) == {"ESPN": 0, "SLEEPER": 0}

    def test_counts_split(self, agg):
        items = [
            {"platform": "ESPN", "onboarded_at": "2024-01-01T00:00:00Z"},
            {"platform": "ESPN", "onboarded_at": "2024-01-02T00:00:00Z"},
            {"platform": "SLEEPER", "onboarded_at": "2024-01-03T00:00:00Z"},
        ]
        assert agg.platform_counts(agg.build_dataframe(items)) == {
            "ESPN": 2,
            "SLEEPER": 1,
        }

    def test_none_platform_ignored(self, agg):
        items = [
            {"onboarded_at": "2024-01-01T00:00:00Z"},  # no platform -> None
            {"platform": "SLEEPER", "onboarded_at": "2024-01-02T00:00:00Z"},
        ]
        assert agg.platform_counts(agg.build_dataframe(items)) == {
            "ESPN": 0,
            "SLEEPER": 1,
        }


# ---- cumulative_series --------------------------------------------------------


class TestCumulativeSeries:
    def test_empty(self, agg):
        series = agg.cumulative_series(agg.build_dataframe([]))
        assert list(series.columns) == ["onboarded_at", "cumulative_count"]
        assert series.empty

    def test_sorted_and_monotonic(self, agg):
        items = [
            {"platform": "ESPN", "onboarded_at": "2024-03-01T00:00:00Z"},
            {"platform": "ESPN", "onboarded_at": "2024-01-01T00:00:00Z"},
            {"platform": "ESPN", "onboarded_at": "2024-02-01T00:00:00Z"},
        ]
        series = agg.cumulative_series(agg.build_dataframe(items))
        assert list(series["cumulative_count"]) == [1, 2, 3]
        assert series["onboarded_at"].is_monotonic_increasing
        assert series.iloc[0]["onboarded_at"] == pd.Timestamp("2024-01-01T00:00:00Z")

    def test_drops_rows_without_onboarded_at(self, agg):
        items = [
            {"platform": "ESPN", "onboarded_at": "bad"},
            {"platform": "ESPN", "onboarded_at": "2024-01-01T00:00:00Z"},
        ]
        series = agg.cumulative_series(agg.build_dataframe(items))
        assert len(series) == 1
        assert list(series["cumulative_count"]) == [1]
