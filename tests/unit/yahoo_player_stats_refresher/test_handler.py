"""Tests for the Yahoo player-data refresher (src/yahoo_player_stats_refresher/handler.py)."""

import json
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest


def _players_payload(players):
    """Build a league/players/stats JSON payload from (key, name, pos, points) tuples."""
    coll = {}
    for i, (key, name, pos, pts) in enumerate(players):
        coll[str(i)] = {
            "player": [
                [
                    {"player_key": key},
                    {"name": {"full": name}},
                    {"display_position": pos},
                ],
                {"player_points": {"total": pts}},
            ]
        }
    coll["count"] = len(players)
    return {"fantasy_content": {"league": [{}, {"players": coll}]}}


class TestResolveSeason:
    def test_override(self, yahoo_refresher_handler, monkeypatch):
        monkeypatch.setenv("SEASON", "2023")
        assert yahoo_refresher_handler._resolve_season("461.l.999", "tok") == "2023"

    def test_from_metadata(self, yahoo_refresher_handler):
        payload = {"fantasy_content": {"league": [{"season": "2025"}]}}
        with patch.object(yahoo_refresher_handler, "_get_json", return_value=payload):
            assert yahoo_refresher_handler._resolve_season("461.l.999", "tok") == "2025"


class TestFetchPlayersPage:
    def test_parses_rows(self, yahoo_refresher_handler):
        payload = _players_payload(
            [("461.p.1", "QB One", "QB", "300.5"), ("461.p.2", "RB Two", "RB", "250.0")]
        )
        with patch.object(yahoo_refresher_handler, "_get_json", return_value=payload):
            rows = yahoo_refresher_handler._fetch_players_page("461.l.999", 0, "tok")
        assert rows == [
            {
                "player_key": "461.p.1",
                "name": "QB One",
                "position": "QB",
                "total_points": "300.5",
            },
            {
                "player_key": "461.p.2",
                "name": "RB Two",
                "position": "RB",
                "total_points": "250.0",
            },
        ]


class TestLoadExisting:
    def test_missing_returns_empty(self, yahoo_refresher_handler):
        err = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )
        with patch.object(
            yahoo_refresher_handler.s3_client, "get_object", side_effect=err
        ):
            assert yahoo_refresher_handler._load_existing("b", "k") == {}

    def test_reads_existing(self, yahoo_refresher_handler):
        body = MagicMock()
        body.read.return_value = json.dumps({"461.p.1": {"2024": "100"}}).encode()
        with patch.object(
            yahoo_refresher_handler.s3_client, "get_object", return_value={"Body": body}
        ):
            assert yahoo_refresher_handler._load_existing("b", "k") == {
                "461.p.1": {"2024": "100"}
            }


class TestMain:
    def _run(self, handler, pages, existing_stats=None):
        token_client = MagicMock()
        token_client.get_valid_access_token.return_value = "tok"
        put_calls = {}

        def _put_object(Bucket, Key, Body, ContentType):
            put_calls[Key] = json.loads(Body)

        with (
            patch.object(handler, "yahoo_tokens_from_env", return_value=token_client),
            patch.object(handler, "_resolve_season", return_value="2025"),
            patch.object(handler, "_fetch_players_page", side_effect=pages),
            patch.object(
                handler, "_load_existing", side_effect=[{}, existing_stats or {}]
            ),
            patch.object(handler.s3_client, "put_object", side_effect=_put_object),
        ):
            handler.main()
        return put_calls

    def test_writes_metadata_and_stats(self, yahoo_refresher_handler):
        pages = [
            [
                {
                    "player_key": "461.p.1",
                    "name": "QB One",
                    "position": "QB",
                    "total_points": "300.5",
                },
            ],
            [],  # empty page ends pagination
        ]
        put = self._run(yahoo_refresher_handler, pages)
        assert put["player-metadata/yahoo_nfl_players.json"] == {
            "461.p.1": {"name": "QB One", "position": "QB"}
        }
        assert put["player-stats/yahoo_nfl_player_stats.json"] == {
            "461.p.1": {"2025": "300.5"}
        }

    def test_deep_merges_prior_seasons(self, yahoo_refresher_handler):
        pages = [
            [
                {
                    "player_key": "461.p.1",
                    "name": "QB One",
                    "position": "QB",
                    "total_points": "300.5",
                }
            ],
            [],
        ]
        put = self._run(
            yahoo_refresher_handler, pages, existing_stats={"461.p.1": {"2024": "280"}}
        )
        assert put["player-stats/yahoo_nfl_player_stats.json"]["461.p.1"] == {
            "2024": "280",
            "2025": "300.5",
        }

    def test_respects_max_players(self, yahoo_refresher_handler, monkeypatch):
        monkeypatch.setenv("MAX_PLAYERS", "1")
        pages = [
            [
                {
                    "player_key": "461.p.1",
                    "name": "A",
                    "position": "QB",
                    "total_points": "1",
                },
                {
                    "player_key": "461.p.2",
                    "name": "B",
                    "position": "RB",
                    "total_points": "2",
                },
            ]
        ]
        put = self._run(yahoo_refresher_handler, pages)
        # Capped at 1 player despite the page holding 2.
        assert list(put["player-metadata/yahoo_nfl_players.json"]) == ["461.p.1"]

    def test_missing_service_config_raises(self, yahoo_refresher_handler, monkeypatch):
        # An unpopulated SSM parameter resolves to "" — fail fast with a clear error rather than
        # letting an empty user id reach the token engine as "No Yahoo link for user".
        monkeypatch.setattr(
            yahoo_refresher_handler, "get_secret_from_env_param", lambda env_var: ""
        )
        with pytest.raises(RuntimeError, match="must be configured"):
            yahoo_refresher_handler.main()

    def test_output_key_override(self, yahoo_refresher_handler, monkeypatch):
        monkeypatch.setenv("OUTPUT_KEY", "player-stats/test_yahoo.json")
        pages = [
            [
                {
                    "player_key": "461.p.1",
                    "name": "A",
                    "position": "QB",
                    "total_points": "1",
                }
            ],
            [],
        ]
        put = self._run(yahoo_refresher_handler, pages)
        assert "player-stats/test_yahoo.json" in put
