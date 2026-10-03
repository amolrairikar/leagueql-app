"""Tests for league selection and invocation in backfill_leagues.py."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_SCRIPT = (
    Path(__file__).parents[3] / "scripts" / "utility_scripts" / "backfill_leagues.py"
)


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def backfill():
    mod = _load_module("backfill_leagues", _SCRIPT)
    yield mod
    sys.modules.pop("backfill_leagues", None)


def _lookup_item(canonical: str) -> dict:
    return {"Item": {"canonical_league_id": {"S": canonical}}}


def _row(canonical: str, league_id: str, *seasons: str) -> dict:
    return {
        "canonical_league_id": {"S": canonical},
        "league_id": {"S": league_id},
        "seasons": {"SS": list(seasons)},
    }


# Per-platform GSI2 rows. canon-1 spans two seasons (chain head is league 200).
_GSI2 = {
    "SLEEPER": [
        _row("canon-1", "200", "2024"),
        _row("canon-1", "100", "2023"),
        _row("canon-2", "300", "2024"),
    ],
    "YAHOO": [
        _row("y-owned", "449.l.1", "2024"),
        _row("y-ownerless", "449.l.2", "2024"),
    ],
    "ESPN": [
        _row("e-opted", "555", "2022", "2023"),
        _row("e-not-opted", "666", "2024"),
        _row("e-no-owner", "777", "2024"),
    ],
}

# METADATA keyed by canonical id.
_METADATA = {
    "y-owned": {"owner_user_id": {"S": "user_y"}},
    "y-ownerless": {},
    "e-opted": {
        "owner_user_id": {"S": "user_e"},
        "auto_refresh_enabled": {"BOOL": True},
    },
    "e-not-opted": {
        "owner_user_id": {"S": "user_e2"},
        "auto_refresh_enabled": {"BOOL": False},
    },
    "e-no-owner": {"auto_refresh_enabled": {"BOOL": True}},
}


def _make_client(*, lookup_response=None) -> MagicMock:
    client = MagicMock()

    def query(**kwargs):
        platform = kwargs["ExpressionAttributeValues"][":platform"]["S"]
        return {"Items": _GSI2[platform]}

    def get_item(**kwargs):
        sk = kwargs["Key"]["SK"]["S"]
        if sk == "LEAGUE_LOOKUP":
            return lookup_response if lookup_response is not None else {}
        canonical = kwargs["Key"]["PK"]["S"].removeprefix("LEAGUE#")
        item = _METADATA.get(canonical)
        return {"Item": item} if item is not None else {}

    client.query.side_effect = query
    client.get_item.side_effect = get_item
    return client


def _sleeper(league_id: str, canonical: str) -> dict:
    return {
        "platform": "SLEEPER",
        "league_id": league_id,
        "canonical_league_id": canonical,
        "owner_user_id": None,
        "season": None,
    }


_YAHOO_OWNED = {
    "platform": "YAHOO",
    "league_id": "449.l.1",
    "canonical_league_id": "y-owned",
    "owner_user_id": "user_y",
    "season": None,
}
_ESPN_OPTED = {
    "platform": "ESPN",
    "league_id": "555",
    "canonical_league_id": "e-opted",
    "owner_user_id": "user_e",
    "season": "2023",
}


class TestGetLeagues:
    def test_all_platforms_selects_only_refreshable_leagues(self, backfill, caplog):
        client = _make_client()
        result = backfill.get_leagues(client, "tbl", backfill.PLATFORMS)
        assert result == [
            _sleeper("200", "canon-1"),
            _sleeper("300", "canon-2"),
            _YAHOO_OWNED,
            _ESPN_OPTED,
        ]
        assert "Skipping YAHOO league 449.l.2: no owner_user_id" in caplog.text
        assert "Skipping ESPN league 666: auto-refresh not enabled" in caplog.text
        assert "Skipping ESPN league 777: no owner_user_id" in caplog.text

    def test_sleeper_does_not_read_metadata(self, backfill):
        client = _make_client()
        backfill.get_leagues(client, "tbl", ("SLEEPER",))
        client.get_item.assert_not_called()

    def test_paginates_gsi2(self, backfill):
        client = MagicMock()
        client.query.side_effect = [
            {"Items": [_row("c1", "1", "2024")], "LastEvaluatedKey": {"k": "v"}},
            {"Items": [_row("c2", "2", "2024")]},
        ]
        result = backfill.get_leagues(client, "tbl", ("SLEEPER",))
        assert [r["league_id"] for r in result] == ["1", "2"]
        assert client.query.call_args_list[1].kwargs["ExclusiveStartKey"] == {"k": "v"}

    def test_skips_rows_without_seasons(self, backfill):
        client = MagicMock()
        client.query.return_value = {
            "Items": [
                {
                    "canonical_league_id": {"S": "c1"},
                    "league_id": {"S": "1"},
                    "pending_season": {"S": "2025"},
                }
            ]
        }
        assert backfill.get_leagues(client, "tbl", ("SLEEPER",)) == []


class TestResolveSingleLeague:
    def test_canonical_id_skips_lookup_and_returns_head(self, backfill):
        client = _make_client()
        result = backfill.resolve_single_league(
            client, "tbl", ("SLEEPER",), canonical_league_id="canon-1"
        )
        assert result == [_sleeper("200", "canon-1")]
        client.get_item.assert_not_called()

    def test_canonical_id_searches_all_platforms(self, backfill):
        client = _make_client()
        result = backfill.resolve_single_league(
            client, "tbl", backfill.PLATFORMS, canonical_league_id="e-opted"
        )
        assert result == [_ESPN_OPTED]

    def test_league_id_resolves_canonical_then_filters_to_head(self, backfill):
        # A non-head league ID (100) still resolves to the chain head (200).
        client = _make_client(lookup_response=_lookup_item("canon-1"))
        result = backfill.resolve_single_league(
            client, "tbl", ("SLEEPER",), league_id="100"
        )
        assert result == [_sleeper("200", "canon-1")]
        client.get_item.assert_called_once_with(
            TableName="tbl",
            Key={
                "PK": {"S": "LEAGUE#100#PLATFORM#SLEEPER"},
                "SK": {"S": "LEAGUE_LOOKUP"},
            },
        )

    def test_league_id_uses_platform_in_lookup_key(self, backfill):
        client = _make_client(lookup_response=_lookup_item("y-owned"))
        result = backfill.resolve_single_league(
            client, "tbl", ("YAHOO",), league_id="449.l.1"
        )
        assert result == [_YAHOO_OWNED]
        lookup_call = client.get_item.call_args_list[0]
        assert lookup_call.kwargs["Key"]["PK"]["S"] == "LEAGUE#449.l.1#PLATFORM#YAHOO"

    def test_league_id_requires_single_platform(self, backfill, caplog):
        client = _make_client()
        result = backfill.resolve_single_league(
            client, "tbl", backfill.PLATFORMS, league_id="100"
        )
        assert result == []
        assert "--league-id requires exactly one --platform" in caplog.text
        client.get_item.assert_not_called()

    def test_missing_lookup_item_returns_empty(self, backfill, caplog):
        client = _make_client(lookup_response={})  # no "Item"
        result = backfill.resolve_single_league(
            client, "tbl", ("SLEEPER",), league_id="999"
        )
        assert result == []
        assert "No LEAGUE_LOOKUP" in caplog.text

    def test_canonical_not_among_leagues_returns_empty(self, backfill, caplog):
        client = _make_client()
        result = backfill.resolve_single_league(
            client, "tbl", ("SLEEPER",), canonical_league_id="canon-999"
        )
        assert result == []
        assert "not found among onboarded SLEEPER leagues" in caplog.text

    def test_ineligible_credentialed_league_returns_empty(self, backfill, caplog):
        client = _make_client()
        result = backfill.resolve_single_league(
            client, "tbl", ("ESPN",), canonical_league_id="e-not-opted"
        )
        assert result == []
        assert "auto-refresh not enabled" in caplog.text


class TestParseArgs:
    def test_defaults_to_all_platforms(self, backfill):
        assert backfill.parse_args([]).platforms == ("SLEEPER", "YAHOO", "ESPN")

    def test_platforms_case_insensitive_deduped_and_ordered(self, backfill):
        args = backfill.parse_args(
            ["--platform", "espn", "--platform", "sleeper", "--platform", "ESPN"]
        )
        assert args.platforms == ("SLEEPER", "ESPN")

    def test_refetch_all_defaults_off(self, backfill):
        assert backfill.parse_args([]).refetch_all is False
        assert backfill.parse_args(["--refetch-all"]).refetch_all is True

    def test_rejects_unknown_platform(self, backfill):
        with pytest.raises(SystemExit):
            backfill.parse_args(["--platform", "nfl"])


class TestMain:
    @pytest.fixture
    def clients(self, backfill, monkeypatch):
        ddb = _make_client()
        lam = MagicMock()
        lam.invoke.return_value = {"StatusCode": 202}
        session = MagicMock()
        session.client.side_effect = lambda name: {"dynamodb": ddb, "lambda": lam}[name]
        monkeypatch.setattr(backfill.boto3, "Session", lambda **_: session)
        return ddb, lam

    def test_dry_run_does_not_invoke(self, backfill, clients):
        _, lam = clients
        backfill.main([])
        lam.invoke.assert_not_called()

    def test_execute_invokes_with_platform_payloads(self, backfill, clients):
        _, lam = clients
        backfill.main(
            ["--platform", "YAHOO", "--platform", "ESPN", "--execute", "--yes"]
        )

        payloads = [json.loads(c.kwargs["Payload"]) for c in lam.invoke.call_args_list]
        assert [c.kwargs["FunctionName"] for c in lam.invoke.call_args_list] == [
            "leagueql-onboarder-dev",
            "leagueql-onboarder-dev",
        ]
        yahoo, espn = payloads
        assert yahoo["body"] == {"leagueId": "449.l.1", "platform": "YAHOO"}
        assert yahoo["ownerUserId"] == "user_y"
        assert espn["body"] == {"leagueId": "555", "platform": "ESPN", "season": "2023"}
        assert espn["ownerUserId"] == "user_e"
        for payload in payloads:
            assert payload["requestType"] == "REFRESH"
            assert payload["reprocessAll"] is True
            # Default mode reprocesses S3 raw data; it does not re-fetch history.
            assert payload["refetchAll"] is False

    def test_refetch_all_flag_sends_refetch_all(self, backfill, clients):
        # backend/sleeper-transactions: --refetch-all re-fetches every season from the platform.
        _, lam = clients
        backfill.main(["--platform", "ESPN", "--refetch-all", "--execute", "--yes"])
        payload = json.loads(lam.invoke.call_args_list[0].kwargs["Payload"])
        assert payload["requestType"] == "REFRESH"
        assert payload["reprocessAll"] is True
        assert payload["refetchAll"] is True

    def test_sleeper_payload_has_no_owner_or_season(self, backfill, clients):
        _, lam = clients
        backfill.main(["--platform", "SLEEPER", "--execute", "--yes"])
        payload = json.loads(lam.invoke.call_args_list[0].kwargs["Payload"])
        assert payload["body"] == {"leagueId": "200", "platform": "SLEEPER"}
        assert payload["ownerUserId"] is None
        assert payload["canonicalLeagueId"] == "canon-1"

    def test_non_202_and_exceptions_continue(self, backfill, clients, caplog):
        _, lam = clients
        lam.invoke.side_effect = [{"StatusCode": 500}, RuntimeError("boom")]
        backfill.main(["--platform", "SLEEPER", "--execute", "--yes"])
        assert lam.invoke.call_count == 2
        assert "returned status 500" in caplog.text
        assert "boom" in caplog.text
        assert "Invoked 0/2" in caplog.text

    def test_confirmation_declined_aborts(self, backfill, clients, monkeypatch):
        _, lam = clients
        monkeypatch.setattr("builtins.input", lambda _: "n")
        backfill.main(["--platform", "SLEEPER", "--execute"])
        lam.invoke.assert_not_called()

    def test_confirmation_prompt_names_refetch_mode(
        self, backfill, clients, monkeypatch
    ):
        prompts = []
        monkeypatch.setattr("builtins.input", lambda msg: prompts.append(msg) or "n")
        backfill.main(["--platform", "SLEEPER", "--refetch-all", "--execute"])
        assert "re-fetch ALL seasons" in prompts[0]
