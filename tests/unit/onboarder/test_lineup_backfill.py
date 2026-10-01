"""Tests for onboarder/lineup_backfill.py (backend/yahoo-lineup-backfill)."""

import io
import json
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

LEAGUE = "canon-1"
SEASON_KEY = f"raw-api-data/{LEAGUE}/2025.json"
STORE_KEY = f"raw-api-data/{LEAGUE}/yahoo_rosters/2025.json"
MANIFEST_KEY = f"raw-api-data/{LEAGUE}/manifest.json"


def _client_error(code):
    return botocore.exceptions.ClientError({"Error": {"Code": code}}, "op")


def _matchup_record(week, status="postevent", teams=("t.1", "t.2")):
    return {
        "season": "2025",
        "data_type": f"matchups_week{week}",
        "data": {
            "matchups": [
                {
                    "week": str(week),
                    "status": status,
                    "teams": [{"team_key": f"461.l.100.{t}"} for t in teams],
                }
            ]
        },
    }


def _roster_payload(team_key):
    return {
        "fantasy_content": {
            "team": [
                [{"team_key": team_key}],
                {
                    "roster": {
                        "0": {
                            "players": {
                                "0": {
                                    "player": [
                                        [{"player_key": f"{team_key}.p"}],
                                        {"selected_position": [{"position": "QB"}]},
                                        {"player_points": {"total": "10.5"}},
                                    ]
                                },
                                "count": 1,
                            }
                        }
                    }
                },
            ]
        }
    }


class _FakeS3:
    """Minimal in-memory S3 for get/put/copy."""

    def __init__(self, objects=None):
        self.objects = dict(objects or {})
        self.puts = []
        self.copies = []

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise _client_error("NoSuchKey")
        return {"Body": io.BytesIO(json.dumps(self.objects[Key]).encode())}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[Key] = json.loads(Body)
        self.puts.append(Key)

    def copy_object(self, **kwargs):
        if kwargs["CopySource"]["Key"] not in self.objects:
            raise _client_error("NoSuchKey")
        self.copies.append(kwargs)

    def list_objects_v2(self, Bucket, Prefix):
        keys = [k for k in self.objects if k.startswith(Prefix)]
        return {"Contents": [{"Key": k} for k in keys]} if keys else {}

    def delete_objects(self, Bucket, Delete):
        for obj in Delete["Objects"]:
            self.objects.pop(obj["Key"], None)


class _Response:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _metadata(pending=("2025",), owner="user_1"):
    item = {"PK": {"S": f"LEAGUE#{LEAGUE}"}, "SK": {"S": "METADATA"}}
    if pending:
        item["pending_lineup_seasons"] = {"SS": list(pending)}
    if owner:
        item["owner_user_id"] = {"S": owner}
    return item


@pytest.fixture
def lb(onboarder_lineup_backfill, monkeypatch):
    monkeypatch.setenv("LINEUP_BACKFILL_REQUEST_INTERVAL", "0")
    return onboarder_lineup_backfill


@pytest.fixture
def ctx():
    context = MagicMock()
    context.get_remaining_time_in_millis.return_value = 600_000
    return context


@pytest.fixture
def env(lb):
    """Patch AWS, Yahoo, the token engine, and the queue; return the fakes."""
    ddb = MagicMock()
    ddb.get_item.return_value = {"Item": _metadata()}
    s3 = _FakeS3(
        {SEASON_KEY: [_matchup_record(1), _matchup_record(2)], MANIFEST_KEY: {}}
    )
    get = MagicMock(side_effect=lambda url, **_: _Response(200, _roster_payload("x")))
    tokens = MagicMock()
    tokens.return_value.get_valid_access_token.return_value = "tok"
    send = MagicMock()
    patches = [
        patch.object(lb, "_dynamodb", ddb),
        patch.object(lb, "_s3", s3),
        patch.object(lb.requests, "get", get),
        patch.object(lb, "yahoo_tokens_from_env", tokens),
        patch.object(lb, "send_lineup_backfill_message", send),
    ]
    for p in patches:
        p.start()
    yield MagicMock(ddb=ddb, s3=s3, get=get, tokens=tokens, send=send)
    for p in patches:
        p.stop()


def _update_expressions(ddb):
    return [c.kwargs["UpdateExpression"] for c in ddb.update_item.call_args_list]


class TestCompletedWeeks:
    def test_only_fully_finished_weeks(self, lb):
        records = [
            _matchup_record(1),
            _matchup_record(2, status="midevent"),
            _matchup_record(3, status="preevent"),
            {"season": "2025", "data_type": "settings", "data": {}},
        ]
        assert lb.completed_weeks(records) == {"1": ["461.l.100.t.1", "461.l.100.t.2"]}

    def test_week_with_any_unfinished_matchup_is_skipped(self, lb):
        records = [
            _matchup_record(4, teams=("t.1", "t.2")),
            _matchup_record(4, status="midevent", teams=("t.3", "t.4")),
        ]
        assert lb.completed_weeks(records) == {}

    def test_legacy_matchups_without_status_are_not_finished(self, lb):
        record = _matchup_record(1)
        del record["data"]["matchups"][0]["status"]
        assert lb.completed_weeks([record]) == {}


class TestLease:
    def test_missing_league_drops_message(self, lb, env, ctx):
        env.ddb.get_item.return_value = {}
        assert lb.run_backfill(LEAGUE, 0, ctx) == "league_missing"
        env.ddb.update_item.assert_not_called()
        env.get.assert_not_called()

    def test_missing_league_cleans_up_orphaned_store(self, lb, env, ctx):
        env.ddb.get_item.return_value = {}
        env.s3.objects[STORE_KEY] = {"weeks": {"1": []}}
        assert lb.run_backfill(LEAGUE, 0, ctx) == "league_missing"
        assert STORE_KEY not in env.s3.objects
        assert SEASON_KEY in env.s3.objects

    def test_lease_held_exits_without_fetching(self, lb, env, ctx):
        env.ddb.update_item.side_effect = _client_error(
            "ConditionalCheckFailedException"
        )
        assert lb.run_backfill(LEAGUE, 0, ctx) == "lease_held"
        env.get.assert_not_called()
        assert env.s3.puts == []

    def test_lease_unexpected_error_propagates(self, lb, env, ctx):
        env.ddb.update_item.side_effect = _client_error("InternalServerError")
        with pytest.raises(botocore.exceptions.ClientError):
            lb.run_backfill(LEAGUE, 0, ctx)

    def test_lease_condition_allows_expired_lease(self, lb, env, ctx):
        lb.run_backfill(LEAGUE, 0, ctx)
        acquire = env.ddb.update_item.call_args_list[0].kwargs
        assert "lineup_backfill_lease_until < :now" in acquire["ConditionExpression"]
        assert "attribute_exists(PK)" in acquire["ConditionExpression"]

    def test_lease_released_even_on_error(self, lb, env, ctx):
        env.get.side_effect = RuntimeError("network")
        with pytest.raises(RuntimeError):
            lb.run_backfill(LEAGUE, 0, ctx)
        assert _update_expressions(env.ddb)[-1] == "REMOVE lineup_backfill_lease_until"

    def test_retaken_lease_release_is_tolerated(self, lb, env, ctx):
        env.ddb.get_item.return_value = {"Item": _metadata(pending=())}
        env.ddb.update_item.side_effect = [
            None,
            _client_error("ConditionalCheckFailedException"),
        ]
        assert lb.run_backfill(LEAGUE, 0, ctx) == "nothing_pending"

    def test_release_unexpected_error_propagates(self, lb, env, ctx):
        env.ddb.get_item.return_value = {"Item": _metadata(pending=())}
        env.ddb.update_item.side_effect = [None, _client_error("InternalServerError")]
        with pytest.raises(botocore.exceptions.ClientError):
            lb.run_backfill(LEAGUE, 0, ctx)


class TestSeasonSelection:
    def test_nothing_pending(self, lb, env, ctx):
        env.ddb.get_item.return_value = {"Item": _metadata(pending=())}
        assert lb.run_backfill(LEAGUE, 0, ctx) == "nothing_pending"
        env.get.assert_not_called()
        env.send.assert_not_called()

    def test_newest_pending_season_first(self, lb, env, ctx):
        env.ddb.get_item.return_value = {
            "Item": _metadata(pending=("2018", "2025", "2019"))
        }
        assert lb.run_backfill(LEAGUE, 0, ctx) == "completed"
        assert STORE_KEY in env.s3.objects
        # More seasons pending -> the chain continues with a fresh attempt counter.
        env.send.assert_called_once_with(LEAGUE)

    def test_fetches_each_team_for_each_finished_week(self, lb, env, ctx):
        lb.run_backfill(LEAGUE, 0, ctx)
        urls = [c.args[0] for c in env.get.call_args_list]
        assert urls == [
            lb.team_roster_url("461.l.100.t.1", "1"),
            lb.team_roster_url("461.l.100.t.2", "1"),
            lb.team_roster_url("461.l.100.t.1", "2"),
            lb.team_roster_url("461.l.100.t.2", "2"),
        ]
        assert env.get.call_args.kwargs["headers"] == {"Authorization": "Bearer tok"}
        assert set(env.s3.objects[STORE_KEY]["weeks"]) == {"1", "2"}
        assert env.s3.objects[STORE_KEY]["weeks"]["1"][0]["points"] == "10.5"

    def test_resumes_from_stored_weeks(self, lb, env, ctx):
        env.s3.objects[STORE_KEY] = {"weeks": {"1": [{"player_key": "kept"}]}}
        lb.run_backfill(LEAGUE, 0, ctx)
        urls = [c.args[0] for c in env.get.call_args_list]
        assert all(";week=2/" in url for url in urls)
        assert env.s3.objects[STORE_KEY]["weeks"]["1"] == [{"player_key": "kept"}]

    def test_in_progress_season_skips_unfinished_week(self, lb, env, ctx):
        env.s3.objects[SEASON_KEY] = [
            _matchup_record(1),
            _matchup_record(2, status="midevent"),
        ]
        lb.run_backfill(LEAGUE, 0, ctx)
        assert set(env.s3.objects[STORE_KEY]["weeks"]) == {"1"}

    def test_season_with_nothing_to_fetch_still_completes(self, lb, env, ctx):
        env.s3.objects[STORE_KEY] = {"weeks": {"1": [], "2": []}}
        assert lb.run_backfill(LEAGUE, 0, ctx) == "completed"
        env.get.assert_not_called()

    def test_missing_season_file_completes_with_nothing_fetched(self, lb, env, ctx):
        del env.s3.objects[SEASON_KEY]
        assert lb.run_backfill(LEAGUE, 0, ctx) == "completed"
        env.get.assert_not_called()

    def test_s3_read_error_propagates(self, lb, env, ctx):
        env.s3.get_object = MagicMock(side_effect=_client_error("AccessDenied"))
        with pytest.raises(botocore.exceptions.ClientError):
            lb.run_backfill(LEAGUE, 0, ctx)


class TestPacing:
    def test_requests_are_paced(self, lb, env, ctx, monkeypatch):
        monkeypatch.setenv("LINEUP_BACKFILL_REQUEST_INTERVAL", "1.0")
        with patch.object(lb.time, "sleep") as mock_sleep:
            lb.run_backfill(LEAGUE, 0, ctx)
        # One request at a time: every request after the first waits for the interval.
        assert mock_sleep.call_count >= 3
        assert all(0 < c.args[0] <= 1.0 for c in mock_sleep.call_args_list)

    def test_checkpoints_after_each_week(self, lb, env, ctx):
        lb.run_backfill(LEAGUE, 0, ctx)
        assert env.s3.puts == [STORE_KEY, STORE_KEY]


class TestCompletion:
    def test_publishes_season_and_clears_pending(self, lb, env, ctx):
        assert lb.run_backfill(LEAGUE, 0, ctx) == "completed"
        (copy,) = env.s3.copies
        assert copy["Key"] == MANIFEST_KEY
        assert copy["CopySource"] == {"Bucket": "test-bucket", "Key": MANIFEST_KEY}
        assert copy["MetadataDirective"] == "REPLACE"
        assert copy["Metadata"]["reprocess_seasons"] == "2025"
        assert "DELETE pending_lineup_seasons :s" in _update_expressions(env.ddb)
        # Last pending season -> no further message.
        env.send.assert_not_called()


class TestLeagueDeletedMidRun:
    def test_missing_manifest_drops_league_and_cleans_up_store(self, lb, env, ctx):
        # The delete removed the manifest (and METADATA) after the season file was read.
        del env.s3.objects[MANIFEST_KEY]
        assert lb.run_backfill(LEAGUE, 0, ctx) == "league_deleted"
        assert STORE_KEY not in env.s3.objects
        # Never marks complete (which would recreate a ghost METADATA item) or re-queues.
        assert "DELETE pending_lineup_seasons :s" not in _update_expressions(env.ddb)
        env.send.assert_not_called()
        assert _update_expressions(env.ddb)[-1] == "REMOVE lineup_backfill_lease_until"

    def test_copy_unexpected_error_propagates(self, lb, env, ctx):
        env.s3.copy_object = MagicMock(side_effect=_client_error("AccessDenied"))
        with pytest.raises(botocore.exceptions.ClientError):
            lb.run_backfill(LEAGUE, 0, ctx)

    def test_metadata_gone_at_completion(self, lb, env, ctx):
        env.ddb.update_item.side_effect = [
            None,  # acquire lease
            _client_error("ConditionalCheckFailedException"),  # mark complete
            _client_error("ConditionalCheckFailedException"),  # release lease
        ]
        assert lb.run_backfill(LEAGUE, 0, ctx) == "league_deleted"
        complete = env.ddb.update_item.call_args_list[1].kwargs
        assert complete["ConditionExpression"] == "attribute_exists(PK)"
        assert STORE_KEY not in env.s3.objects

    def test_metadata_gone_when_marking_failed(self, lb, env, ctx):
        env.get.side_effect = [_Response(403)]
        env.ddb.update_item.side_effect = [
            None,
            _client_error("ConditionalCheckFailedException"),
            _client_error("ConditionalCheckFailedException"),
        ]
        assert lb.run_backfill(LEAGUE, 0, ctx) == "league_deleted"

    def test_season_set_update_unexpected_error_propagates(self, lb, env, ctx):
        env.ddb.update_item.side_effect = [
            None,
            _client_error("InternalServerError"),
            None,
        ]
        with pytest.raises(botocore.exceptions.ClientError):
            lb.run_backfill(LEAGUE, 0, ctx)


class TestThrottle:
    def test_999_stops_and_retries_later(self, lb, env, ctx):
        env.get.side_effect = [
            _Response(200, _roster_payload("a")),
            _Response(200, _roster_payload("b")),
            _Response(999),
        ]
        assert lb.run_backfill(LEAGUE, 2, ctx) == "throttled"
        # Week 1 is checkpointed; nothing after the 999 is requested.
        assert set(env.s3.objects[STORE_KEY]["weeks"]) == {"1"}
        assert env.get.call_count == 3
        env.send.assert_called_once_with(LEAGUE, attempt=3, delay_seconds=900)
        assert env.s3.copies == []

    def test_retries_exhausted_marks_failed_and_moves_on(self, lb, env, ctx):
        env.ddb.get_item.return_value = {"Item": _metadata(pending=("2024", "2025"))}
        env.get.side_effect = [_Response(999)]
        assert lb.run_backfill(LEAGUE, 7, ctx) == "retries_exhausted"
        assert (
            "DELETE pending_lineup_seasons :s ADD failed_lineup_seasons :s"
            in _update_expressions(env.ddb)
        )
        env.send.assert_called_once_with(LEAGUE, delay_seconds=900)

    def test_retries_exhausted_on_last_season_ends_chain(self, lb, env, ctx):
        env.get.side_effect = [_Response(999)]
        assert lb.run_backfill(LEAGUE, 7, ctx) == "retries_exhausted"
        env.send.assert_not_called()


class TestPermanentErrors:
    @pytest.mark.parametrize("status", [403, 404])
    def test_no_access_marks_failed_without_retry(self, lb, env, ctx, status):
        env.get.side_effect = [_Response(status)]
        assert lb.run_backfill(LEAGUE, 0, ctx) == "failed"
        assert (
            "DELETE pending_lineup_seasons :s ADD failed_lineup_seasons :s"
            in _update_expressions(env.ddb)
        )
        env.send.assert_not_called()

    def test_401_retried_once_then_succeeds(self, lb, env, ctx):
        env.get.side_effect = [_Response(401)] + [
            _Response(200, _roster_payload("x"))
        ] * 4
        assert lb.run_backfill(LEAGUE, 0, ctx) == "completed"

    def test_repeated_401_is_permanent(self, lb, env, ctx):
        env.get.side_effect = [_Response(401), _Response(401)]
        assert lb.run_backfill(LEAGUE, 0, ctx) == "failed"

    def test_revoked_link_marks_failed(self, lb, env, ctx):
        env.tokens.return_value.get_valid_access_token.side_effect = (
            lb.YahooReauthRequired("revoked")
        )
        assert lb.run_backfill(LEAGUE, 0, ctx) == "failed"
        env.send.assert_not_called()

    def test_missing_owner_marks_failed(self, lb, env, ctx):
        env.ddb.get_item.return_value = {"Item": _metadata(owner=None)}
        assert lb.run_backfill(LEAGUE, 0, ctx) == "failed"
        env.get.assert_not_called()

    def test_transient_http_error_propagates_for_sqs_redelivery(self, lb, env, ctx):
        env.get.side_effect = [_Response(503)]
        with pytest.raises(RuntimeError, match="503"):
            lb.run_backfill(LEAGUE, 0, ctx)
        env.send.assert_not_called()


class TestTimeBudget:
    def test_out_of_time_requeues_with_same_attempt(self, lb, env, ctx):
        ctx.get_remaining_time_in_millis.side_effect = [600_000, 1_000]
        assert lb.run_backfill(LEAGUE, 3, ctx) == "out_of_time"
        assert set(env.s3.objects[STORE_KEY]["weeks"]) == {"1"}
        env.send.assert_called_once_with(LEAGUE, attempt=3)
        assert env.s3.copies == []


class TestLambdaHandler:
    def test_runs_one_pass_per_record(self, lb, ctx):
        event = {
            "Records": [
                {"body": json.dumps({"canonical_league_id": "a", "attempt": 2})},
                {"body": json.dumps({"canonical_league_id": "b"})},
            ]
        }
        with patch.object(lb, "run_backfill", return_value="completed") as mock_run:
            assert lb.lambda_handler(event, ctx) == {
                "outcomes": ["completed", "completed"]
            }
        assert [c.args[:2] for c in mock_run.call_args_list] == [("a", 2), ("b", 0)]
