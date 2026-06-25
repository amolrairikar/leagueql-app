"""Unit tests for the recap-drainer Lambda (BE-022)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


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
) -> MagicMock:
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
        cond = kwargs["KeyConditionExpression"]
        if cond.get_expression()["operator"] == "=":
            # PK == RECAP_QUEUE marker scan.
            return {"Items": markers}
        prefix = _sk_begins_with_prefix(cond)
        season = prefix.split("#")[1]
        if prefix.startswith("MATCHUP_RECAP#"):
            return {
                "Items": [
                    {"SK": f"MATCHUP_RECAP#{season}#WEEK#{w}"}
                    for w in existing_by_season.get(season, [])
                ]
            }
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


@pytest.fixture
def patched(drainer):
    """Patch the drainer's table, S3 and batch submission. Defaults to one premium
    league with a single missing week."""
    table = make_table(
        markers=[_pending("123")],
        metadata={"subscription_end_time": _future_iso()},
        seasons=["2024"],
        weeks_by_season={"2024": {"01": [_matchup()]}},
        standings_by_season={"2024": [{"team_id": "1", "record": "1-0-0"}]},
    )
    with (
        patch.object(drainer, "_table", table),
        patch.object(drainer, "_s3") as s3,
        patch.object(drainer, "submit_batch_job", return_value="arn:job:1") as submit,
    ):
        yield drainer, table, s3, submit


class TestDrainHappyPath:
    def test_submits_job_for_missing_week(self, patched):
        drainer, table, s3, submit = patched
        result = drainer._handle()

        assert result["status"] == "submitted"
        assert result["records"] == 1
        assert result["leagues"] == 1
        # JSONL written to S3, then job submitted.
        s3.put_object.assert_called_once()
        body = s3.put_object.call_args.kwargs["Body"].decode("utf-8")
        assert '"recordId"' in body and '"modelInput"' in body
        submit.assert_called_once()
        # Manifest written + marker flipped to in_flight.
        manifest = next(
            c.kwargs["Item"]
            for c in table.put_item.call_args_list
            if c.kwargs["Item"]["PK"].startswith("RECAP_JOB#")
        )
        assert manifest["league_ids"] == ["123"]
        assert list(manifest["records"].values())[0] == {
            "canonical_league_id": "123",
            "season": "2024",
            "week": "01",
        }
        update = table.update_item.call_args.kwargs
        assert update["ExpressionAttributeValues"][":inflight"] == "in_flight"
        assert update["ExpressionAttributeValues"][":job"] == "arn:job:1"


class TestGating:
    def test_billing_disabled_skips(self, patched):
        from common import feature_flags

        drainer, table, s3, submit = patched
        feature_flags._override_for_testing({"billing": False})
        result = drainer._handle()
        assert result["status"] == "skipped"
        submit.assert_not_called()

    def test_no_markers_completes(self, drainer):
        table = make_table(
            markers=[],
            metadata={},
            seasons=[],
            weeks_by_season={},
            standings_by_season={},
        )
        with patch.object(drainer, "_table", table):
            result = drainer._handle()
        assert result == {"status": "completed", "submitted": 0, "records": 0}

    def test_non_premium_drops_marker_no_spend(self, drainer):
        table = make_table(
            markers=[_pending("123")],
            metadata={},  # no subscription_end_time → not active
            seasons=["2024"],
            weeks_by_season={"2024": {"01": [_matchup()]}},
            standings_by_season={"2024": []},
        )
        with (
            patch.object(drainer, "_table", table),
            patch.object(drainer, "_s3"),
            patch.object(drainer, "submit_batch_job") as submit,
        ):
            result = drainer._handle()
        assert result["records"] == 0
        submit.assert_not_called()
        table.delete_item.assert_called_once()
        assert table.delete_item.call_args.kwargs["Key"]["SK"] == "PENDING#123"

    def test_fully_recapped_clears_marker(self, drainer):
        table = make_table(
            markers=[_pending("123")],
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {"01": [_matchup()]}},
            standings_by_season={"2024": []},
            existing_by_season={"2024": ["01"]},  # already recapped
        )
        with (
            patch.object(drainer, "_table", table),
            patch.object(drainer, "_s3"),
            patch.object(drainer, "submit_batch_job") as submit,
        ):
            result = drainer._handle()
        assert result["records"] == 0
        submit.assert_not_called()
        table.delete_item.assert_called_once()


class TestMinBatchSize:
    def test_below_minimum_holds(self, patched):
        drainer, table, s3, submit = patched
        with patch.object(drainer, "_MIN_BATCH_RECORDS", 5):
            result = drainer._handle()
        assert result["status"] == "held"
        assert result["records"] == 1
        submit.assert_not_called()
        s3.put_object.assert_not_called()
        # Marker is left untouched (not flipped, not deleted).
        table.update_item.assert_not_called()


class TestStaleInFlight:
    def test_stale_in_flight_is_resubmitted(self, drainer):
        old = (datetime.now(timezone.utc) - timedelta(hours=99)).isoformat()
        table = make_table(
            markers=[_pending("123", status="in_flight", submitted_at=old)],
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {"01": [_matchup()]}},
            standings_by_season={"2024": []},
        )
        with (
            patch.object(drainer, "_table", table),
            patch.object(drainer, "_s3"),
            patch.object(
                drainer, "submit_batch_job", return_value="arn:job:2"
            ) as submit,
        ):
            result = drainer._handle()
        assert result["status"] == "submitted"
        submit.assert_called_once()

    def test_fresh_in_flight_is_skipped(self, drainer):
        recent = datetime.now(timezone.utc).isoformat()
        table = make_table(
            markers=[_pending("123", status="in_flight", submitted_at=recent)],
            metadata={"subscription_end_time": _future_iso()},
            seasons=["2024"],
            weeks_by_season={"2024": {"01": [_matchup()]}},
            standings_by_season={"2024": []},
        )
        with (
            patch.object(drainer, "_table", table),
            patch.object(drainer, "_s3"),
            patch.object(drainer, "submit_batch_job") as submit,
        ):
            result = drainer._handle()
        # No drainable markers → completed no-op.
        assert result == {"status": "completed", "submitted": 0, "records": 0}
        submit.assert_not_called()
