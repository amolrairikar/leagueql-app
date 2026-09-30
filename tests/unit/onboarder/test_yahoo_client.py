"""Unit tests for the Yahoo onboarding client (src/onboarder/yahoo_client.py)."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def yc(onboarder_yahoo_client):
    return onboarder_yahoo_client


# A real (trimmed) Yahoo ``team/{key}/roster;week=2/players/stats;type=week;week=2`` response:
# a started QB, a benched WR, and a DEF, with Yahoo's full nesting kept intact.
_TEAM_ROSTER_WEEK2 = Path(__file__).parent / "fixtures" / "yahoo_team_roster_week2.json"


def _team_roster_payload(team_key="470.l.1676376.t.1"):
    data = json.loads(_TEAM_ROSTER_WEEK2.read_text())
    data["fantasy_content"]["team"][0][0] = {"team_key": team_key}
    return data


# --------------------------------------------------------------------------------------
# Canned Yahoo JSON builders (translated from Yahoo's documented XML shapes)
# --------------------------------------------------------------------------------------
def _league_meta(league_key, league_id, season, renew=None, **extra):
    meta = {
        "league_key": league_key,
        "league_id": league_id,
        "season": season,
        "start_week": "1",
        "end_week": "17",
        "current_week": "5",
        "num_teams": "2",
    }
    if renew:
        meta["renew"] = renew
    meta.update(extra)
    return meta


def _user_leagues_payload(leagues):
    """leagues: list of (game_key, league_meta) grouped one league per game node."""
    games = {}
    for i, (game_key, meta) in enumerate(leagues):
        games[str(i)] = {
            "game": [
                {"game_key": game_key, "game_code": "nfl"},
                {"leagues": {"0": {"league": [meta]}, "count": 1}},
            ]
        }
    games["count"] = len(leagues)
    return {
        "fantasy_content": {
            "users": {"0": {"user": [{}, {"games": games}]}, "count": 1}
        }
    }


def _league_payload(subresource_key, subresource_value, meta=None):
    return {
        "fantasy_content": {
            "league": [meta or {}, {subresource_key: subresource_value}]
        }
    }


class TestResolveSeasons:
    def test_full_history_via_renew_chain(self, yc):
        payload = _user_leagues_payload(
            [
                ("461", _league_meta("461.l.100", "100", "2025", renew="449_90")),
                ("449", _league_meta("449.l.90", "90", "2024")),
            ]
        )
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                **{"json.return_value": payload, "raise_for_status": MagicMock()}
            )
            client = yc.YahooClient("100", "user_1", token_provider=lambda: "tok")
        assert client.get_seasons() == ["2024", "2025"]
        assert client._season_meta["2025"]["league_key"] == "461.l.100"
        assert client._season_meta["2024"]["league_key"] == "449.l.90"

    def test_refresh_current_season_only(self, yc):
        payload = _user_leagues_payload(
            [
                ("461", _league_meta("461.l.100", "100", "2025", renew="449_90")),
                ("449", _league_meta("449.l.90", "90", "2024")),
            ]
        )
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                **{"json.return_value": payload, "raise_for_status": MagicMock()}
            )
            client = yc.YahooClient(
                "100", "user_1", is_refresh=True, token_provider=lambda: "tok"
            )
        assert client.get_seasons() == ["2025"]

    def test_not_a_member_raises(self, yc):
        payload = _user_leagues_payload(
            [("461", _league_meta("461.l.100", "100", "2025"))]
        )
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                **{"json.return_value": payload, "raise_for_status": MagicMock()}
            )
            with pytest.raises(ValueError, match="not among"):
                yc.YahooClient("999", "user_1", token_provider=lambda: "tok")

    def test_bearer_header_used_for_resolution(self, yc):
        payload = _user_leagues_payload(
            [("461", _league_meta("461.l.100", "100", "2025"))]
        )
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                **{"json.return_value": payload, "raise_for_status": MagicMock()}
            )
            yc.YahooClient("100", "user_1", token_provider=lambda: "tok-xyz")
        assert mock_get.call_args.kwargs["headers"]["Authorization"] == "Bearer tok-xyz"


@pytest.fixture
def client(yc):
    """A resolved single-season client (network stubbed for construction)."""
    payload = _user_leagues_payload([("461", _league_meta("461.l.100", "100", "2025"))])
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            **{"json.return_value": payload, "raise_for_status": MagicMock()}
        )
        return yc.YahooClient("100", "user_1", token_provider=lambda: "tok")


class TestBuildRequestUrls:
    def test_includes_all_subresources_and_weeks(self, client):
        urls = client._build_request_urls()
        data_types = {dt for _, dt, _ in urls}
        assert {
            "settings",
            "standings",
            "teams",
            "draft_picks",
            "transactions",
            "game_weeks",
        } <= data_types
        # The week calendar is per game: league key "461.l.100" -> game key "461".
        game_weeks_url = next(url for _, dt, url in urls if dt == "game_weeks")
        assert "/game/461/game_weeks" in game_weeks_url
        # current_week=5 -> matchup weeks 1..5
        matchup_weeks = sorted(
            int(dt.removeprefix("matchups_week"))
            for _, dt, _ in urls
            if dt.startswith("matchups_week")
        )
        assert matchup_weeks == [1, 2, 3, 4, 5]
        # num_teams=2 -> one weekly roster+stats call per team, per week.
        roster_urls = {dt: url for _, dt, url in urls if dt.startswith("rosters")}
        assert set(roster_urls) == {
            f"rosters_week{w}_t{t}" for w in range(1, 6) for t in (1, 2)
        }
        assert roster_urls["rosters_week3_t2"].endswith(
            "/team/461.l.100.t.2/roster;week=3/players/stats;type=week;week=3?format=json"
        )
        assert all(
            url.endswith("?format=json") or ";week=" in url for _, _, url in urls
        )

    def test_skips_rosters_without_num_teams(self, yc):
        meta = _league_meta("461.l.100", "100", "2025")
        del meta["num_teams"]
        payload = _user_leagues_payload([("461", meta)])
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                **{"json.return_value": payload, "raise_for_status": MagicMock()}
            )
            client = yc.YahooClient("100", "user_1", token_provider=lambda: "tok")
        data_types = [dt for _, dt, _ in client._build_request_urls()]
        assert not [dt for dt in data_types if dt.startswith("rosters")]
        assert "matchups_week1" in data_types


class TestFilters:
    def test_game_weeks(self, yc):
        data = {
            "fantasy_content": {
                "game": [
                    {"game_key": "461", "season": "2025"},
                    {
                        "game_weeks": {
                            "0": {
                                "game_week": {
                                    "week": "1",
                                    "display_name": "1",
                                    "start": "2025-09-04",
                                    "end": "2025-09-08",
                                }
                            },
                            "1": {
                                "game_week": {
                                    "week": "2",
                                    "display_name": "2",
                                    "start": "2025-09-09",
                                    "end": "2025-09-15",
                                }
                            },
                            "count": 2,
                        }
                    },
                ]
            }
        }
        out = yc._filter_game_weeks(data, "2025", "game_weeks")
        assert out == {
            "game_weeks": [
                {"week": "1", "start": "2025-09-04", "end": "2025-09-08"},
                {"week": "2", "start": "2025-09-09", "end": "2025-09-15"},
            ]
        }

    def test_game_weeks_missing(self, yc):
        assert yc._filter_game_weeks({}, "2025", "game_weeks") == {"game_weeks": []}

    def test_settings(self, yc):
        data = _league_payload(
            "settings",
            [{"num_playoff_teams": "6", "playoff_start_week": "15"}],
            meta={"league_key": "461.l.100", "name": "My League"},
        )
        out = yc._filter_settings(data, "2025", "settings")
        assert out == {
            "name": "My League",
            "num_playoff_teams": "6",
            "playoff_start_week": "15",
        }

    def test_standings(self, yc):
        data = _league_payload(
            "standings",
            [
                {
                    "teams": {
                        "0": {
                            "team": [
                                [{"team_key": "461.l.100.t.1"}],
                                {"team_standings": {"rank": "1"}},
                            ]
                        },
                        "count": 1,
                    }
                }
            ],
        )
        out = yc._filter_standings(data, "2025", "standings")
        assert out == {"standings": [{"team_key": "461.l.100.t.1", "rank": "1"}]}

    def test_teams_members_and_managers(self, yc):
        data = _league_payload(
            "teams",
            {
                "0": {
                    "team": [
                        [
                            {"team_key": "461.l.100.t.1"},
                            {"team_id": "1"},
                            {"name": "Team A"},
                            # Yahoo returns these nested sub-collections as plain lists.
                            {"team_logos": [{"team_logo": {"url": "http://logo"}}]},
                            {
                                "managers": [
                                    {
                                        "manager": {
                                            "manager_id": "1",
                                            "nickname": "Alice",
                                            "guid": "G1",
                                        }
                                    }
                                ]
                            },
                        ]
                    ]
                },
                "count": 1,
            },
        )
        out = yc._filter_teams(data, "2025", "teams")
        assert out["members"] == [{"manager_id": "G1", "nickname": "Alice"}]
        assert out["teams"] == [
            {
                "team_key": "461.l.100.t.1",
                "team_id": "1",
                "name": "Team A",
                "logo": "http://logo",
                "manager_id": "G1",
            }
        ]

    def test_teams_masked_guids_fall_back_to_manager_id(self, yc):
        """Yahoo masks the guid in some (e.g. public) leagues, returning the SAME value for
        every manager; owner ids must come from the distinct per-league manager_id so teams
        don't all collapse onto one manager."""

        def _team(idx, nick):
            return {
                "team": [
                    [
                        {"team_key": f"461.l.100.t.{idx}"},
                        {"team_id": str(idx)},
                        {"name": f"Team {nick}"},
                        {
                            "managers": [
                                {
                                    "manager": {
                                        "manager_id": str(idx),
                                        "nickname": nick,
                                        "guid": "MASKED",
                                    }
                                }
                            ]
                        },
                    ]
                ]
            }

        data = _league_payload(
            "teams",
            {"0": _team(1, "Alice"), "1": _team(2, "Bob"), "count": 2},
        )
        out = yc._filter_teams(data, "2025", "teams")
        assert out["members"] == [
            {"manager_id": "1", "nickname": "Alice"},
            {"manager_id": "2", "nickname": "Bob"},
        ]
        assert [t["manager_id"] for t in out["teams"]] == ["1", "2"]

    def test_matchups(self, yc):
        data = _league_payload(
            "scoreboard",
            {
                "0": {
                    "matchups": {
                        "0": {
                            "matchup": {
                                "week": "1",
                                "is_playoffs": "0",
                                "is_consolation": "0",
                                "winner_team_key": "461.l.100.t.1",
                                "0": {
                                    "teams": {
                                        "0": {
                                            "team": [
                                                [{"team_key": "461.l.100.t.1"}],
                                                {"team_points": {"total": "100.5"}},
                                            ]
                                        },
                                        "1": {
                                            "team": [
                                                [{"team_key": "461.l.100.t.2"}],
                                                {"team_points": {"total": "90.0"}},
                                            ]
                                        },
                                        "count": 2,
                                    }
                                },
                            }
                        },
                        "count": 1,
                    }
                },
                "week": "1",
            },
        )
        out = yc._filter_matchups(data, "2025", "matchups_week1")
        m = out["matchups"][0]
        assert m["week"] == "1"
        assert m["winner_team_key"] == "461.l.100.t.1"
        assert m["teams"] == [
            {"team_key": "461.l.100.t.1", "points": "100.5"},
            {"team_key": "461.l.100.t.2", "points": "90.0"},
        ]

    def test_rosters(self, yc):
        out = yc._filter_rosters(_team_roster_payload(), "2026", "rosters_week2_t1")
        assert out["rosters"] == [
            {
                "team_key": "470.l.1676376.t.1",
                "week": "2",
                "player_key": "470.p.40896",
                "player_name": "Jayden Daniels",
                "position": "QB",
                "selected_position": "QB",
                "points": "14.74",
            },
            {
                "team_key": "470.l.1676376.t.1",
                "week": "2",
                "player_key": "470.p.31908",
                "player_name": "Terry McLaurin",
                "position": "WR",
                "selected_position": "BN",
                "points": "6.00",
            },
            {
                "team_key": "470.l.1676376.t.1",
                "week": "2",
                "player_key": "470.p.100007",
                "player_name": "Broncos",
                "position": "DEF",
                "selected_position": "DEF",
                "points": "8.00",
            },
        ]

    def test_rosters_empty_payload(self, yc):
        assert yc._filter_rosters({}, "2026", "rosters_week2_t1") == {"rosters": []}

    def test_draft_picks(self, yc):
        data = _league_payload(
            "draft_results",
            {
                "0": {
                    "draft_result": {
                        "pick": "1",
                        "round": "1",
                        "team_key": "461.l.100.t.1",
                        "player_key": "461.p.100",
                    }
                },
                "count": 1,
            },
        )
        out = yc._filter_draft_picks(data, "2025", "draft_picks")
        assert out["draft_picks"] == [
            {
                "pick": "1",
                "round": "1",
                "team_key": "461.l.100.t.1",
                "player_key": "461.p.100",
                "cost": None,
            }
        ]

    def test_transactions_kept_and_normalized(self, yc):
        data = _league_payload(
            "transactions",
            {
                "0": {
                    "transaction": [
                        {
                            "transaction_key": "461.l.100.tr.1",
                            "type": "add/drop",
                            "status": "successful",
                            "timestamp": "1700000000",
                        },
                        {
                            "players": {
                                "0": {
                                    "player": [
                                        [{"player_key": "461.p.100"}],
                                        {
                                            "transaction_data": [
                                                {
                                                    "type": "add",
                                                    "destination_team_key": "461.l.100.t.1",
                                                }
                                            ]
                                        },
                                    ]
                                },
                                "count": 1,
                            }
                        },
                    ]
                },
                "count": 1,
            },
        )
        out = yc._filter_transactions(data, "2025", "transactions")
        assert out["transactions"] == [
            {
                "transaction_key": "461.l.100.tr.1",
                "type": "add/drop",
                "timestamp": "1700000000",
                "faab_bid": None,
                "items": [
                    {
                        "player_key": "461.p.100",
                        "type": "add",
                        "source_team_key": None,
                        "destination_team_key": "461.l.100.t.1",
                    }
                ],
            }
        ]

    def test_transactions_drops_pending_and_commish(self, yc):
        data = _league_payload(
            "transactions",
            {
                "0": {
                    "transaction": [
                        {"type": "add", "status": "pending"},
                        {"players": {"count": 0}},
                    ]
                },
                "1": {
                    "transaction": [
                        {"type": "commish", "status": "successful"},
                        {"players": {"count": 0}},
                    ]
                },
                "count": 2,
            },
        )
        out = yc._filter_transactions(data, "2025", "transactions")
        assert out["transactions"] == []


class TestProcessApiResults:
    def test_applies_filters_and_validates(self, client):
        results = [
            {
                "season": "2025",
                "data_type": "settings",
                "data": _league_payload(
                    "settings",
                    [{"num_playoff_teams": "6", "playoff_start_week": "15"}],
                    meta={"name": "My League"},
                ),
            }
        ]
        processed = client._process_api_results(results)
        assert processed[0]["data"]["name"] == "My League"

    def test_merges_per_team_rosters_into_one_weekly_record(self, client):
        results = [
            {
                "season": "2026",
                "data_type": "rosters_week2_t1",
                "data": _team_roster_payload("470.l.1676376.t.1"),
            },
            {
                "season": "2026",
                "data_type": "matchups_week2",
                "data": _league_payload("scoreboard", {"0": {"matchups": {}}}),
            },
            {
                "season": "2026",
                "data_type": "rosters_week2_t2",
                "data": _team_roster_payload("470.l.1676376.t.2"),
            },
            {
                "season": "2026",
                "data_type": "rosters_week3_t1",
                "data": _team_roster_payload("470.l.1676376.t.1"),
            },
        ]
        processed = client._process_api_results(results)
        assert [p["data_type"] for p in processed] == [
            "rosters_week2",
            "matchups_week2",
            "rosters_week3",
        ]
        week2 = processed[0]["data"]["rosters"]
        assert len(week2) == 6
        assert {r["team_key"] for r in week2} == {
            "470.l.1676376.t.1",
            "470.l.1676376.t.2",
        }
        assert {r["week"] for r in week2} == {"2"}
        week3 = processed[2]["data"]["rosters"]
        assert len(week3) == 3
        assert {r["week"] for r in week3} == {"3"}

    def test_raises_on_failed_fetch(self, client):
        results = [{"season": "2025", "data_type": "settings", "data": None}]
        with pytest.raises(RuntimeError):
            client._process_api_results(results)


class TestFetchAsync:
    def test_fetch_success(self, client, yc):
        sem = asyncio.Semaphore(1)
        with patch.object(
            yc, "fetch_with_retry", new=AsyncMock(return_value={"ok": True})
        ):
            result = asyncio.run(
                client._fetch(MagicMock(), sem, ("2025", "settings", "http://u"))
            )
        assert result == {
            "season": "2025",
            "data_type": "settings",
            "data": {"ok": True},
        }

    def test_fetch_returns_none_on_error(self, client, yc):
        sem = asyncio.Semaphore(1)
        with patch.object(
            yc, "fetch_with_retry", new=AsyncMock(side_effect=RuntimeError("boom"))
        ):
            result = asyncio.run(
                client._fetch(MagicMock(), sem, ("2025", "settings", "http://u"))
            )
        assert result["data"] is None

    def test_auth_retry_refreshes_on_401(self, client, yc):
        import aiohttp

        err = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=401
        )
        mock_fetch = AsyncMock(side_effect=[err, {"ok": True}])
        with patch.object(yc, "fetch_with_retry", new=mock_fetch):
            result = asyncio.run(client._fetch_with_auth_retry(MagicMock(), "http://u"))
        assert result == {"ok": True}
        assert mock_fetch.call_count == 2

    def test_auth_retry_reraises_non_401(self, client, yc):
        import aiohttp

        err = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=500
        )
        with (
            patch.object(yc, "fetch_with_retry", new=AsyncMock(side_effect=err)),
            pytest.raises(aiohttp.ClientResponseError),
        ):
            asyncio.run(client._fetch_with_auth_retry(MagicMock(), "http://u"))
