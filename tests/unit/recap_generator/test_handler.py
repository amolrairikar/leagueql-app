"""Unit tests for the recap-generator Fargate task (BE-022)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError


def _future_iso(days: int = 1) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _matchup() -> dict:
    return {
        "team_a_id": "1",
        "team_a_display_name": "alice",
        "team_a_team_name": "Alice's Team",
        "team_a_score": 120.5,
        "team_a_starters": [
            {"full_name": "QB One", "position": "QB", "points_scored": 30.0},
            {"full_name": "RB One", "position": "RB", "points_scored": 25.0},
        ],
        "team_a_bench": [
            {"full_name": "Bench A", "position": "WR", "points_scored": 18.0}
        ],
        "team_b_id": "2",
        "team_b_display_name": "bob",
        "team_b_team_name": "Bob's Team",
        "team_b_score": 90.0,
        "team_b_starters": [
            {"full_name": "QB Two", "position": "QB", "points_scored": 12.0}
        ],
        "team_b_bench": [],
        "playoff_round": None,
        "winner": "1",
        "week": "01",
        "season": "2024",
    }


def _sk_begins_with_prefix(condition) -> str | None:
    expr = condition.get_expression()
    for value in expr.get("values", []):
        if hasattr(value, "get_expression"):
            inner = value.get_expression()
            if inner.get("operator") == "begins_with":
                return inner["values"][1]
    return None


def make_table(
    *,
    markers: list[dict],
    metadata: dict,
    seasons: list[str],
    weeks_by_season: dict[str, dict[str, list]],
    standings_by_season: dict[str, list],
    existing_by_season: dict[str, list[str]] | None = None,
    weekly_by_season: dict[str, list] | None = None,
) -> MagicMock:
    existing_by_season = existing_by_season or {}
    weekly_by_season = weekly_by_season or {}
    table = MagicMock()

    def get_item(Key, **_):
        sk = Key["SK"]
        if sk == "METADATA":
            return {"Item": metadata} if metadata else {}
        if sk.startswith("WEEKLY_STANDINGS#"):
            season = sk.split("#")[1]
            return {"Item": {"data": weekly_by_season.get(season, [])}}
        if sk.startswith("STANDINGS#"):
            season = sk.split("#")[1]
            return {"Item": {"data": standings_by_season.get(season, [])}}
        return {}

    def query(**kwargs):
        if kwargs.get("IndexName") == "GSI1":
            return {"Items": [{"seasons": set(seasons)}]}
        prefix = _sk_begins_with_prefix(kwargs["KeyConditionExpression"])
        if prefix and prefix.startswith("PENDING#"):
            return {"Items": markers}
        if prefix and prefix.startswith("MATCHUP_RECAP#"):
            season = prefix.split("#")[1]
            return {
                "Items": [
                    {"SK": f"MATCHUP_RECAP#{season}#WEEK#{w}"}
                    for w in existing_by_season.get(season, [])
                ]
            }
        season = prefix.split("#")[1]
        return {
            "Items": [
                {"SK": f"MATCHUPS#{season}#WEEK#{w}", "data": data}
                for w, data in weeks_by_season.get(season, {}).items()
            ]
        }

    table.get_item.side_effect = get_item
    table.query.side_effect = query
    return table


def _pending(league: str = "123", **extra) -> dict:
    return {
        "PK": "RECAP_QUEUE",
        "SK": f"PENDING#{league}",
        "canonical_league_id": league,
        "status": "pending",
        "correlation_id": "cid",
        **extra,
    }


_RECAP = {"headline": "Big Week", "body": "Para one.\n\nPara two."}


@pytest.fixture
def patched(generator):
    """One premium league with a single missing week; generate_recap stubbed."""
    table = make_table(
        markers=[_pending("123")],
        metadata={"subscription_end_time": _future_iso()},
        seasons=["2024"],
        weeks_by_season={"2024": {"01": [_matchup()]}},
        standings_by_season={"2024": [{"team_id": "1", "record": "1-0-0"}]},
    )
    with (
        patch.object(generator, "_table", table),
        patch.object(generator, "generate_recap", return_value=_RECAP) as gen,
        patch.object(generator, "_throttle") as throttle,
    ):
        yield generator, table, gen, throttle


class TestHappyPath:
    def test_writes_recap_and_clears_marker(self, patched):
        generator, table, gen, throttle = patched
        result = generator._handle()

        assert result["status"] == "completed"
        assert result["written"] == 1
        assert result["failed"] == 0
        gen.assert_called_once()
        throttle.assert_called_once()
        # Conditional put of the MATCHUP_RECAP item.
        put = table.put_item.call_args.kwargs
        assert put["Item"]["SK"] == "MATCHUP_RECAP#2024#WEEK#01"
        assert put["ConditionExpression"] == "attribute_not_exists(SK)"
        recap = put["Item"]["data"][0]
        assert recap["headline"] == "Big Week"
        assert recap["body"] == "Para one.\n\nPara two."
        assert recap["model"] == "claude-haiku-4-5"
        # Marker cleared on full success.
        table.delete_item.assert_called_once()
        assert table.delete_item.call_args.kwargs["Key"]["SK"] == "PENDING#123"


class TestGating:
    def test_billing_disabled_skips(self, patched):
        from common import feature_flags

        generator, table, gen, throttle = patched
        feature_flags._override_for_testing({"billing": False})
        result = generator._handle()
        assert result["status"] == "skipped"
        gen.assert_not_called()

    def test_no_markers_completes(self, generator):
        table = make_table(
            markers=[],
            metadata={},
            seasons=[],
            weeks_by_season={},
            standings_by_season={},
        )
        with patch.object(generator, "_table", table):
            result = generator._handle()
        assert result == {
            "status": "completed",
            "leagues": 0,
            "written": 0,
            "failed": 0,
        }

    def test_non_premium_drops_marker_no_spend(self, generator):
        table = make_table(
            markers=[_pending("123")],
            metadata={},  # no subscription_end_time → not active
            seasons=["2024"],
            weeks_by_season={"2024": {"01": [_matchup()]}},
            standings_by_season={"2024": []},
        )
        with (
            patch.object(generator, "_table", table),
            patch.object(generator, "generate_recap") as gen,
            patch.object(generator, "_throttle"),
        ):
            result = generator._handle()
        assert result["written"] == 0
        gen.assert_not_called()
        table.delete_item.assert_called_once()
        assert table.delete_item.call_args.kwargs["Key"]["SK"] == "PENDING#123"

    def test_fully_recapped_clears_marker(self, generator):
        table = make_table(
            markers=[_pending("123")],
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {"01": [_matchup()]}},
            standings_by_season={"2024": []},
            existing_by_season={"2024": ["01"]},  # already recapped
        )
        with (
            patch.object(generator, "_table", table),
            patch.object(generator, "generate_recap") as gen,
            patch.object(generator, "_throttle"),
        ):
            result = generator._handle()
        assert result["written"] == 0
        gen.assert_not_called()
        table.delete_item.assert_called_once()


class TestIdempotency:
    def test_conditional_check_failed_is_not_a_failure(self, patched):
        generator, table, gen, throttle = patched
        table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
        )
        result = generator._handle()
        # Already-present item → not counted as written, not a failure; marker cleared.
        assert result["written"] == 0
        assert result["failed"] == 0
        table.delete_item.assert_called_once()

    def test_other_client_error_propagates_as_failure(self, patched):
        generator, table, gen, throttle = patched
        table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException"}}, "PutItem"
        )
        result = generator._handle()
        assert result["failed"] == 1
        # Marker left pending for the next run.
        table.delete_item.assert_not_called()


class TestWeekAccurateRecord:
    def _highlights_for(self, gen) -> dict:
        # generate_recap is called positionally with the week's highlights dict.
        return (
            gen.call_args.args[0]
            if gen.call_args.args
            else gen.call_args.kwargs["highlights"]
        )

    def test_uses_weekly_record_not_final_season_record(self, generator):
        # Final standings says 5-8-0; the Week 7 snapshot says 5-2-0 — the recap must
        # see the as-of-week record, not the end-of-season record.
        table = make_table(
            markers=[_pending("123")],
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {"07": [_matchup()]}},
            standings_by_season={"2024": [{"team_id": "1", "record": "5-8-0"}]},
            weekly_by_season={
                "2024": [{"snapshot_week": "7", "team_id": "1", "record": "5-2-0"}]
            },
        )
        with (
            patch.object(generator, "_table", table),
            patch.object(generator, "generate_recap", return_value=_RECAP) as gen,
            patch.object(generator, "_throttle"),
        ):
            generator._handle()
        highlights = self._highlights_for(gen)
        assert highlights["matchups"][0]["team_a"]["record"] == "5-2-0"

    def test_falls_back_to_final_standings_when_week_has_no_snapshot(self, generator):
        # A playoff week ("15") with no WEEKLY_STANDINGS snapshot falls back to the
        # final standings record.
        table = make_table(
            markers=[_pending("123")],
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {"15": [_matchup()]}},
            standings_by_season={"2024": [{"team_id": "1", "record": "9-5-0"}]},
            weekly_by_season={
                "2024": [{"snapshot_week": "7", "team_id": "1", "record": "5-2-0"}]
            },
        )
        with (
            patch.object(generator, "_table", table),
            patch.object(generator, "generate_recap", return_value=_RECAP) as gen,
            patch.object(generator, "_throttle"),
        ):
            generator._handle()
        highlights = self._highlights_for(gen)
        assert highlights["matchups"][0]["team_a"]["record"] == "9-5-0"


class TestPartialFailure:
    def test_failed_week_leaves_marker_and_writes_others(self, generator):
        table = make_table(
            markers=[_pending("123")],
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {"01": [_matchup()], "02": [_matchup()]}},
            standings_by_season={"2024": []},
        )
        with (
            patch.object(generator, "_table", table),
            patch.object(
                generator,
                "generate_recap",
                side_effect=[_RECAP, RuntimeError("rate limited")],
            ) as gen,
            patch.object(generator, "_throttle"),
        ):
            result = generator._handle()
        assert gen.call_count == 2
        assert result["written"] == 1
        assert result["failed"] == 1
        # One week written, but the marker stays pending for the next run.
        assert table.put_item.call_count == 1
        table.delete_item.assert_not_called()
