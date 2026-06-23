"""Tests for recap/handler.py (DynamoDB faked in-memory; generate_recap mocked)."""

import datetime
from unittest.mock import MagicMock

import pytest


class FakeTable:
    """Minimal in-memory stand-in for a boto3 DynamoDB Table resource.

    ``query`` returns every stored item whose SK begins with ``MATCHUPS#`` (the only
    query the handler issues); ``get_item`` / ``put_item`` work by exact PK+SK.
    """

    def __init__(self, items=None):
        self.store = {}
        for item in items or []:
            self.store[(item["PK"], item["SK"])] = item
        self.puts = []

    def get_item(self, Key, **kwargs):
        item = self.store.get((Key["PK"], Key["SK"]))
        return {"Item": item} if item is not None else {}

    def query(self, **kwargs):
        items = [v for (pk, sk), v in self.store.items() if sk.startswith("MATCHUPS#")]
        return {"Items": items}

    def put_item(self, Item):
        self.puts.append(Item)
        self.store[(Item["PK"], Item["SK"])] = Item


def _future_iso():
    return (
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    ).isoformat()


def _past_iso():
    return "1970-01-01T00:00:00+00:00"


def _metadata(cid="cid-1", end_time=None):
    item = {"PK": f"LEAGUE#{cid}", "SK": "METADATA"}
    if end_time is not None:
        item["subscription_end_time"] = end_time
    return item


def _matchups_item(cid="cid-1", season="2025", ww="01"):
    return {
        "PK": f"LEAGUE#{cid}",
        "SK": f"MATCHUPS#{season}#WEEK#{ww}",
        "data": [
            {
                "team_a_id": "1",
                "team_a_display_name": "alice",
                "team_a_score": 100,
                "team_a_starters": [],
                "team_a_bench": [],
                "team_b_id": "2",
                "team_b_display_name": "bob",
                "team_b_score": 90,
                "team_b_starters": [],
                "team_b_bench": [],
            }
        ],
    }


def _recap_item(cid="cid-1", season="2025", ww="01"):
    return {
        "PK": f"LEAGUE#{cid}",
        "SK": f"RECAP#{season}#WEEK#{ww}",
        "data": [{"headline": "old", "body": "old"}],
    }


@pytest.fixture
def patched(recap_handler, monkeypatch):
    """Patch the handler's collaborators and return a small control surface."""
    monkeypatch.setattr(recap_handler, "is_feature_paywalled", lambda flag: True)
    job_status = MagicMock()
    monkeypatch.setattr(recap_handler, "write_job_status", job_status)
    gen = MagicMock(return_value={"headline": "H", "body": "B", "model": "test-model"})
    monkeypatch.setattr(recap_handler, "generate_recap", gen)

    def set_table(table):
        monkeypatch.setattr(recap_handler, "_table", lambda: table)

    return SimpleControl(recap_handler, job_status, gen, set_table)


class SimpleControl:
    def __init__(self, handler, job_status, gen, set_table):
        self.handler = handler
        self.job_status = job_status
        self.gen = gen
        self.set_table = set_table


def _event(cid="cid-1", correlation_id="corr-1"):
    return {"canonical_league_id": cid, "correlation_id": correlation_id}


class TestLambdaHandler:
    def test_skips_when_no_league(self, patched):
        result = patched.handler.lambda_handler({}, MagicMock())
        assert result["status"] == "skipped"
        assert result["reason"] == "no_league"
        patched.gen.assert_not_called()

    def test_skips_when_not_paywalled(self, patched, monkeypatch):
        monkeypatch.setattr(patched.handler, "is_feature_paywalled", lambda flag: False)
        result = patched.handler.lambda_handler(_event(), MagicMock())
        assert result["reason"] == "not_paywalled"
        patched.gen.assert_not_called()

    def test_skips_when_subscription_inactive(self, patched):
        # METADATA present but expired in the past.
        patched.set_table(FakeTable([_metadata(end_time=_past_iso())]))
        result = patched.handler.lambda_handler(_event(), MagicMock())
        assert result["reason"] == "subscription_inactive"
        patched.gen.assert_not_called()

    def test_skips_when_metadata_missing(self, patched):
        patched.set_table(FakeTable([]))
        result = patched.handler.lambda_handler(_event(), MagicMock())
        assert result["reason"] == "subscription_inactive"

    def test_skips_when_end_time_unparseable(self, patched):
        patched.set_table(FakeTable([_metadata(end_time="garbage")]))
        result = patched.handler.lambda_handler(_event(), MagicMock())
        assert result["reason"] == "subscription_inactive"

    def test_generates_all_missing_weeks(self, patched):
        table = FakeTable(
            [
                _metadata(end_time=_future_iso()),
                _matchups_item(ww="01"),
                _matchups_item(ww="02"),
            ]
        )
        patched.set_table(table)
        result = patched.handler.lambda_handler(_event(), MagicMock())
        assert result["status"] == "completed"
        assert result["generated"] == 2
        assert result["skipped"] == 0
        assert result["failed"] == 0
        assert len(table.puts) == 2
        # RECAP items written with the single-element list shape + model + week.
        recap = next(p for p in table.puts if p["SK"] == "RECAP#2025#WEEK#01")
        assert recap["data"][0]["week"] == "1"
        assert recap["data"][0]["headline"] == "H"
        # The model recorded is whatever the orchestrator returned for the recap.
        assert recap["data"][0]["model"] == "test-model"
        patched.job_status.assert_called_once()
        assert patched.job_status.call_args.args[1] == "COMPLETED"

    def test_idempotent_skips_existing_recap(self, patched):
        table = FakeTable(
            [
                _metadata(end_time=_future_iso()),
                _matchups_item(ww="01"),
                _matchups_item(ww="02"),
                _recap_item(ww="01"),  # already generated
            ]
        )
        patched.set_table(table)
        result = patched.handler.lambda_handler(_event(), MagicMock())
        assert result["generated"] == 1
        assert result["skipped"] == 1
        assert patched.gen.call_count == 1

    def test_malformed_matchups_sk_ignored(self, patched):
        bad = _matchups_item(ww="01")
        bad["SK"] = "MATCHUPS#2025#BADKEY"
        table = FakeTable([_metadata(end_time=_future_iso()), bad])
        patched.set_table(table)
        result = patched.handler.lambda_handler(_event(), MagicMock())
        assert result["generated"] == 0
        patched.gen.assert_not_called()

    def test_recap_generation_error_marks_failed(self, patched, monkeypatch):
        monkeypatch.setattr(
            patched.handler,
            "generate_recap",
            MagicMock(side_effect=patched.handler.RecapGenerationError("refused")),
        )
        table = FakeTable([_metadata(end_time=_future_iso()), _matchups_item(ww="01")])
        patched.set_table(table)
        result = patched.handler.lambda_handler(_event(), MagicMock())
        assert result["status"] == "failed"
        assert result["failed"] == 1
        assert result["generated"] == 0
        assert table.puts == []
        assert patched.job_status.call_args.args[1] == "FAILED"
        assert patched.job_status.call_args.kwargs["failure_code"] == "RECAP"

    def test_unexpected_error_marks_failed(self, patched, monkeypatch):
        monkeypatch.setattr(
            patched.handler,
            "generate_recap",
            MagicMock(side_effect=RuntimeError("boom")),
        )
        table = FakeTable([_metadata(end_time=_future_iso()), _matchups_item(ww="01")])
        patched.set_table(table)
        result = patched.handler.lambda_handler(_event(), MagicMock())
        assert result["status"] == "failed"
        assert result["failed"] == 1

    def test_no_matchups_completes_with_nothing(self, patched):
        patched.set_table(FakeTable([_metadata(end_time=_future_iso())]))
        result = patched.handler.lambda_handler(_event(), MagicMock())
        assert result["status"] == "completed"
        assert result["generated"] == 0
        assert patched.job_status.call_args.args[1] == "COMPLETED"

    def test_mixed_success_and_failure_tallied(self, patched, monkeypatch):
        # One week succeeds, one raises — the loop tallies both outcomes correctly
        # and writes only the successful week's RECAP item.
        def _gen(highlights, season, week):
            if week == "2":
                raise patched.handler.RecapGenerationError("refused week 2")
            return {"headline": "H", "body": "B", "model": "test-model"}

        monkeypatch.setattr(patched.handler, "generate_recap", _gen)
        table = FakeTable(
            [
                _metadata(end_time=_future_iso()),
                _matchups_item(ww="01"),
                _matchups_item(ww="02"),
            ]
        )
        patched.set_table(table)
        result = patched.handler.lambda_handler(_event(), MagicMock())
        assert result["status"] == "failed"
        assert result["generated"] == 1
        assert result["failed"] == 1
        assert [p["SK"] for p in table.puts] == ["RECAP#2025#WEEK#01"]
