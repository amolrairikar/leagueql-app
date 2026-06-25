"""Unit tests for the recap-generator Lambda (BE-022)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


def _future_iso(days: int = 1) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _past_iso(days: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _matchup(week_pad: str = "01") -> dict:
    """A single normal matchup row (team A beats team B)."""
    return {
        "team_a_id": "1",
        "team_a_display_name": "alice",
        "team_a_team_name": "Alice's Team",
        "team_a_score": 120.5,
        "team_a_starters": [
            {"full_name": "QB One", "position": "QB", "points_scored": 30.0},
            {"full_name": "RB One", "position": "RB", "points_scored": 25.0},
            {"full_name": "WR One", "position": "WR", "points_scored": 10.0},
        ],
        "team_a_bench": [
            {"full_name": "Bench A", "position": "WR", "points_scored": 18.0},
        ],
        "team_b_id": "2",
        "team_b_display_name": "bob",
        "team_b_team_name": "Bob's Team",
        "team_b_score": 90.0,
        "team_b_starters": [
            {"full_name": "QB Two", "position": "QB", "points_scored": 12.0},
        ],
        "team_b_bench": [],
        "playoff_round": None,
        "winner": "1",
        "loser": "2",
        "week": week_pad,
        "season": "2024",
    }


def _standings_rows() -> list[dict]:
    return [
        {"team_id": "1", "record": "1-0-0"},
        {"team_id": "2", "record": "0-1-0"},
    ]


def _sk_begins_with_prefix(condition) -> str | None:
    """Pull the ``begins_with`` literal out of a ``PK.eq & SK.begins_with`` key cond."""
    expr = condition.get_expression()
    for value in expr.get("values", []):
        if hasattr(value, "get_expression"):
            inner = value.get_expression()
            if inner.get("operator") == "begins_with":
                return inner["values"][1]
    return None


def make_table(
    *,
    metadata: dict,
    seasons: list[str],
    weeks_by_season: dict[str, dict[str, list]],
    standings_by_season: dict[str, list],
    existing_by_season: dict[str, list[str]] | None = None,
) -> MagicMock:
    """Build a fake DynamoDB Table whose get_item/query reflect the seeded data."""
    existing_by_season = existing_by_season or {}
    table = MagicMock()

    def get_item(Key, **_):
        sk = Key["SK"]
        if sk == "METADATA":
            return {"Item": metadata} if metadata else {}
        if sk.startswith("STANDINGS#"):
            season = sk.split("#")[1]
            return {"Item": {"data": standings_by_season.get(season, [])}}
        return {}

    def query(**kwargs):
        if kwargs.get("IndexName") == "GSI1":
            return {"Items": [{"seasons": set(seasons)}]}
        prefix = _sk_begins_with_prefix(kwargs["KeyConditionExpression"])
        season = prefix.split("#")[1]
        if prefix.startswith("MATCHUP_RECAP#"):
            return {
                "Items": [
                    {"SK": f"MATCHUP_RECAP#{season}#WEEK#{w}"}
                    for w in existing_by_season.get(season, [])
                ]
            }
        # MATCHUPS#{season}# prefix
        return {
            "Items": [
                {"SK": f"MATCHUPS#{season}#WEEK#{w}", "data": data}
                for w, data in weeks_by_season.get(season, {}).items()
            ]
        }

    table.get_item.side_effect = get_item
    table.query.side_effect = query
    return table


@pytest.fixture
def patched(recap_handler):
    """Patch the handler's table + Bedrock call; default to a generated recap."""
    with (
        patch.object(recap_handler, "generate_recap") as gen,
        patch.object(recap_handler, "_table") as table,
    ):
        gen.return_value = {"headline": "Big Week", "body": "Para one.\n\nPara two."}
        yield recap_handler, gen, table


class TestGate:
    def test_missing_canonical_id_skips(self, patched):
        rh, gen, _ = patched
        resp = rh.lambda_handler({}, None)
        assert resp["status"] == "skipped"
        gen.assert_not_called()

    def test_billing_disabled_noop(self, patched):
        from common import feature_flags

        feature_flags._override_for_testing({"billing": False})
        rh, gen, table = patched
        resp = rh.lambda_handler({"canonical_league_id": "cid"}, None)
        assert resp["reason"] == "billing_disabled"
        gen.assert_not_called()
        table.put_item.assert_not_called()

    def test_non_premium_league_skips_without_bedrock(self, patched):
        rh, gen, _ = patched
        rh._table = make_table(
            metadata={"subscription_end_time": _past_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {"01": [_matchup()]}},
            standings_by_season={"2024": _standings_rows()},
        )
        with patch.object(rh, "_table", rh._table):
            resp = rh.lambda_handler({"canonical_league_id": "cid"}, None)
        assert resp["reason"] == "not_premium"
        gen.assert_not_called()

    def test_absent_subscription_skips(self, patched):
        rh, gen, _ = patched
        with patch.object(
            rh,
            "_table",
            make_table(
                metadata={},
                seasons=["2024"],
                weeks_by_season={"2024": {"01": [_matchup()]}},
                standings_by_season={"2024": _standings_rows()},
            ),
        ):
            resp = rh.lambda_handler({"canonical_league_id": "cid"}, None)
        assert resp["reason"] == "not_premium"
        gen.assert_not_called()


class TestGeneration:
    def test_generates_all_seasons_and_weeks(self, patched):
        rh, gen, _ = patched
        table = make_table(
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2023", "2024"],
            weeks_by_season={
                "2023": {"01": [_matchup()], "02": [_matchup("02")]},
                "2024": {"01": [_matchup()]},
            },
            standings_by_season={
                "2023": _standings_rows(),
                "2024": _standings_rows(),
            },
        )
        with patch.object(rh, "_table", table):
            resp = rh.lambda_handler({"canonical_league_id": "cid"}, None)
        assert resp == {"status": "completed", "generated": 3}
        assert gen.call_count == 3
        assert table.put_item.call_count == 3

    def test_item_shape(self, patched):
        rh, _, _ = patched
        table = make_table(
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {"01": [_matchup()]}},
            standings_by_season={"2024": _standings_rows()},
        )
        with patch.object(rh, "_table", table):
            rh.lambda_handler({"canonical_league_id": "cid"}, None)
        item = table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "LEAGUE#cid"
        assert item["SK"] == "MATCHUP_RECAP#2024#WEEK#01"
        assert isinstance(item["data"], list)
        recap = item["data"][0]
        assert recap["headline"] == "Big Week"
        assert recap["body"] == "Para one.\n\nPara two."
        assert recap["model"] == "us.meta.llama3-3-70b-instruct-v1:0"
        assert "generated_at" in recap

    def test_idempotent_skip_existing_weeks(self, patched):
        rh, gen, _ = patched
        table = make_table(
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {"01": [_matchup()], "02": [_matchup("02")]}},
            standings_by_season={"2024": _standings_rows()},
            existing_by_season={"2024": ["01"]},  # week 1 already recapped
        )
        with patch.object(rh, "_table", table):
            resp = rh.lambda_handler({"canonical_league_id": "cid"}, None)
        assert resp["generated"] == 1
        gen.assert_called_once()
        assert table.put_item.call_args.kwargs["Item"]["SK"].endswith("WEEK#02")

    def test_all_weeks_already_recapped_is_noop(self, patched):
        rh, gen, _ = patched
        table = make_table(
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {"01": [_matchup()]}},
            standings_by_season={"2024": _standings_rows()},
            existing_by_season={"2024": ["01"]},
        )
        with patch.object(rh, "_table", table):
            resp = rh.lambda_handler({"canonical_league_id": "cid"}, None)
        assert resp == {"status": "completed", "generated": 0}
        gen.assert_not_called()

    def test_no_seasons_is_noop(self, patched):
        rh, gen, _ = patched
        table = make_table(
            metadata={"subscription_end_time": _future_iso()},
            seasons=[],
            weeks_by_season={},
            standings_by_season={},
        )
        with patch.object(rh, "_table", table):
            resp = rh.lambda_handler({"canonical_league_id": "cid"}, None)
        assert resp == {"status": "completed", "generated": 0}
        gen.assert_not_called()

    def test_season_with_no_weeks_skipped(self, patched):
        rh, gen, _ = patched
        table = make_table(
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {}},
            standings_by_season={"2024": _standings_rows()},
        )
        with patch.object(rh, "_table", table):
            resp = rh.lambda_handler({"canonical_league_id": "cid"}, None)
        assert resp["generated"] == 0
        gen.assert_not_called()

    def test_one_week_failure_does_not_abort_batch(self, patched):
        rh, gen, _ = patched
        # First call raises, the rest succeed — the failing week is dropped, others
        # are still written (idempotent skip retries it on a later invoke).
        gen.side_effect = [
            RuntimeError("bedrock throttled"),
            {"headline": "H", "body": "B"},
        ]
        table = make_table(
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {"01": [_matchup()], "02": [_matchup("02")]}},
            standings_by_season={"2024": _standings_rows()},
        )
        with patch.object(rh, "_table", table):
            resp = rh.lambda_handler({"canonical_league_id": "cid"}, None)
        assert resp["generated"] == 1
        assert table.put_item.call_count == 1


class TestHighlights:
    def test_self_matchup_bye_is_skipped(self, recap_handler):
        bye = _matchup()
        bye["team_b_id"] = "1"  # self-matchup placeholder
        highlights = recap_handler._build_highlights(
            "2024", "01", [bye, _matchup()], {"1": {"record": "1-0-0"}}
        )
        assert len(highlights["matchups"]) == 1
        assert highlights["week"] == 1

    def test_highlights_trim_top_performers_and_record(self, recap_handler):
        highlights = recap_handler._build_highlights(
            "2024",
            "01",
            [_matchup()],
            {"1": {"record": "1-0-0"}, "2": {"record": "0-1-0"}},
        )
        game = highlights["matchups"][0]
        assert game["winner"] == "alice"
        assert game["margin"] == 30.5
        # Trimmed to the top 2 starters by points, top 1 bench.
        assert len(game["team_a"]["top_starters"]) == 2
        assert game["team_a"]["top_starters"][0]["name"] == "QB One"
        assert len(game["team_a"]["top_bench"]) == 1
        assert game["team_a"]["record"] == "1-0-0"


class TestHelperBranches:
    def test_convert_decimals_int_and_float(self, recap_handler):
        from decimal import Decimal

        out = recap_handler._convert_decimals(
            {"a": Decimal("2"), "b": Decimal("1.5"), "c": ["x", Decimal("3")]}
        )
        assert out == {"a": 2, "b": 1.5, "c": ["x", 3]}

    def test_subscription_active_invalid_date_is_inactive(self, recap_handler):
        assert (
            recap_handler._is_subscription_active(
                {"subscription_end_time": "not-a-date"}
            )
            is False
        )

    def test_matchup_weeks_paginates(self, recap_handler):
        table = MagicMock()
        table.query.side_effect = [
            {
                "Items": [{"SK": "MATCHUPS#2024#WEEK#01", "data": []}],
                "LastEvaluatedKey": {"k": 1},
            },
            {"Items": [{"SK": "MATCHUPS#2024#WEEK#02", "data": []}]},
        ]
        with patch.object(recap_handler, "_table", table):
            weeks = recap_handler._get_matchup_weeks("cid", "2024")
        assert set(weeks) == {"01", "02"}
        assert table.query.call_count == 2

    def test_existing_recap_weeks_paginates(self, recap_handler):
        table = MagicMock()
        table.query.side_effect = [
            {
                "Items": [{"SK": "MATCHUP_RECAP#2024#WEEK#01"}],
                "LastEvaluatedKey": {"k": 1},
            },
            {"Items": [{"SK": "MATCHUP_RECAP#2024#WEEK#02"}]},
        ]
        with patch.object(recap_handler, "_table", table):
            existing = recap_handler._get_existing_recap_weeks("cid", "2024")
        assert existing == {"01", "02"}
        assert table.query.call_count == 2


class TestTracing:
    def test_handler_continues_trace_from_carrier(self, recap_handler):
        event = {
            "canonical_league_id": "cid",
            "trace_context": {"traceparent": "00-abc-def-01"},
        }
        with (
            patch.object(recap_handler, "_handle", return_value={"status": "ok"}),
            patch.object(recap_handler, "traced_handler") as th,
        ):
            recap_handler.lambda_handler(event, None)
        th.assert_called_once_with(
            "recap_generator.handle", carrier={"traceparent": "00-abc-def-01"}
        )

    def test_handler_passes_none_carrier_when_absent(self, recap_handler):
        with (
            patch.object(
                recap_handler, "_handle", return_value={"status": "ok"}
            ) as impl,
            patch.object(recap_handler, "traced_handler") as th,
        ):
            recap_handler.lambda_handler({"canonical_league_id": "cid"}, None)
            # _handle still receives the event.
            impl.assert_called_once_with({"canonical_league_id": "cid"})
        th.assert_called_once_with("recap_generator.handle", carrier=None)
