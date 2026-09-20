"""Tests for the shared Yahoo members fetch/parse (src/common/yahoo_members.py)."""

from unittest.mock import MagicMock

import pytest

from common import yahoo_members
from common.yahoo_members import (
    YahooLeagueNotFound,
    fetch_yahoo_members,
    parse_managers,
    resolve_league_key,
)

# ── Fixtures / builders ─────────────────────────────────────────────────────────


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


def _league_meta(league_key, league_id):
    return {"league_key": league_key, "league_id": league_id, "season": "2025"}


def _teams_payload(teams):
    """teams: list of attribute-lists (each a flat list of single-key dicts)."""
    collection = {str(i): {"team": [attrs]} for i, attrs in enumerate(teams)}
    collection["count"] = len(teams)
    return {"fantasy_content": {"league": [{}, {"teams": collection}]}}


def _manager(**fields):
    # Yahoo returns a team's nested ``managers`` as a plain list (not a numeric-keyed
    # collection), which is what the parser must handle.
    return {"managers": [{"manager": fields}]}


def _http_returning(*payloads):
    """A requests-like mock whose .get returns each payload's response in order."""
    http = MagicMock()
    responses = []
    for payload in payloads:
        resp = MagicMock()
        resp.json.return_value = payload
        responses.append(resp)
    http.get.side_effect = responses
    return http


# ── Pure helpers ────────────────────────────────────────────────────────────────


class TestFlatten:
    def test_merges_list_of_single_key_dicts(self):
        assert yahoo_members._flatten([{"a": 1}, {"b": 2}]) == {"a": 1, "b": 2}

    def test_merges_nested_lists(self):
        assert yahoo_members._flatten([[{"a": 1}], {"b": 2}]) == {"a": 1, "b": 2}

    def test_dict_returned_as_is(self):
        assert yahoo_members._flatten({"a": 1}) == {"a": 1}

    def test_non_container_returns_empty(self):
        assert yahoo_members._flatten("nope") == {}


class TestCollectionItems:
    def test_returns_indexed_inner_objects(self):
        container = {"0": {"team": "A"}, "1": {"team": "B"}, "count": 2}
        assert yahoo_members._collection_items(container, "team") == ["A", "B"]

    def test_stops_at_first_gap(self):
        container = {"0": {"team": "A"}, "2": {"team": "C"}, "count": 2}
        assert yahoo_members._collection_items(container, "team") == ["A"]

    def test_returns_plain_list_inner_objects(self):
        # Yahoo's small nested sub-collections (managers, team_logos) come as plain lists.
        container = [{"manager": "A"}, {"manager": "B"}]
        assert yahoo_members._collection_items(container, "manager") == ["A", "B"]

    def test_plain_list_skips_elements_without_inner_key(self):
        container = [{"manager": "A"}, [], {"other": "X"}]
        assert yahoo_members._collection_items(container, "manager") == ["A"]

    def test_non_dict_returns_empty(self):
        assert yahoo_members._collection_items(None, "team") == []


class TestLeagueSubresource:
    def test_finds_trailing_subresource(self):
        payload = {"fantasy_content": {"league": [{"meta": 1}, {"teams": "T"}]}}
        assert yahoo_members._league_subresource(payload, "teams") == "T"

    def test_missing_returns_none(self):
        payload = {"fantasy_content": {"league": [{"meta": 1}]}}
        assert yahoo_members._league_subresource(payload, "teams") is None


# ── resolve_league_key ────────────────────────────────────────────────────────────


class TestResolveLeagueKey:
    def test_resolves_entered_id_to_key(self):
        payload = _user_leagues_payload(
            [
                ("461", _league_meta("461.l.100", "100")),
                ("461", _league_meta("461.l.200", "200")),
            ]
        )
        assert resolve_league_key(payload, "200") == "461.l.200"

    def test_id_coerced_to_string(self):
        payload = _user_leagues_payload([("461", _league_meta("461.l.100", "100"))])
        assert resolve_league_key(payload, 100) == "461.l.100"

    def test_missing_id_returns_none(self):
        payload = _user_leagues_payload([("461", _league_meta("461.l.100", "100"))])
        assert resolve_league_key(payload, "999") is None


# ── parse_managers ────────────────────────────────────────────────────────────────


class TestParseManagers:
    def test_uses_guid_and_nickname(self):
        payload = _teams_payload(
            [
                [
                    {"team_key": "t.1"},
                    _manager(manager_id="1", guid="G1", nickname="Alice"),
                ]
            ]
        )
        assert parse_managers(payload) == [{"owner_id": "G1", "display_name": "Alice"}]

    def test_falls_back_to_manager_id_when_no_guid(self):
        payload = _teams_payload(
            [[{"team_key": "t.1"}, _manager(manager_id="7", nickname="Bob")]]
        )
        assert parse_managers(payload) == [{"owner_id": "7", "display_name": "Bob"}]

    def test_display_name_falls_back_to_owner_id(self):
        payload = _teams_payload([[{"team_key": "t.1"}, _manager(guid="G2")]])
        assert parse_managers(payload) == [{"owner_id": "G2", "display_name": "G2"}]

    def test_skips_team_without_manager_id(self):
        payload = _teams_payload([[{"team_key": "t.1"}, _manager(nickname="Ghost")]])
        assert parse_managers(payload) == []

    def test_duplicate_guids_fall_back_to_manager_id(self):
        # Yahoo masks the guid in some leagues, returning the SAME value for every manager;
        # owner ids must then come from the distinct per-league manager_id, not collapse.
        payload = _teams_payload(
            [
                [
                    {"team_key": "t.1"},
                    _manager(manager_id="1", guid="SAME", nickname="A"),
                ],
                [
                    {"team_key": "t.2"},
                    _manager(manager_id="2", guid="SAME", nickname="B"),
                ],
            ]
        )
        assert parse_managers(payload) == [
            {"owner_id": "1", "display_name": "A"},
            {"owner_id": "2", "display_name": "B"},
        ]

    def test_empty_teams(self):
        assert parse_managers(_teams_payload([])) == []


class TestResolveTeamOwnerIds:
    @staticmethod
    def _team_flat(**manager_fields):
        return {"managers": [{"manager": manager_fields}]}

    def test_distinct_guids_used(self):
        flats = [
            self._team_flat(manager_id="1", guid="G1"),
            self._team_flat(manager_id="2", guid="G2"),
        ]
        assert yahoo_members.resolve_team_owner_ids(flats) == ["G1", "G2"]

    def test_duplicate_guids_fall_back_to_manager_id(self):
        flats = [
            self._team_flat(manager_id="1", guid="X"),
            self._team_flat(manager_id="2", guid="X"),
        ]
        assert yahoo_members.resolve_team_owner_ids(flats) == ["1", "2"]

    def test_partial_guids_fall_back_to_manager_id(self):
        flats = [
            self._team_flat(manager_id="1"),
            self._team_flat(manager_id="2", guid="G2"),
        ]
        assert yahoo_members.resolve_team_owner_ids(flats) == ["1", "2"]

    def test_no_manager(self):
        assert yahoo_members.resolve_team_owner_ids([{}]) == [None]


# ── fetch_yahoo_members ───────────────────────────────────────────────────────────


class TestFetchYahooMembers:
    def test_happy_path(self):
        leagues = _user_leagues_payload([("461", _league_meta("461.l.100", "100"))])
        teams = _teams_payload(
            [[{"team_key": "t.1"}, _manager(guid="G1", nickname="Alice")]]
        )
        http = _http_returning(leagues, teams)

        result = fetch_yahoo_members("access-tok", "100", http=http)

        assert result == [{"owner_id": "G1", "display_name": "Alice"}]
        # First call enumerates leagues; second fetches the resolved league's teams.
        first_url = http.get.call_args_list[0].args[0]
        second_url = http.get.call_args_list[1].args[0]
        assert "games;game_codes=nfl/leagues" in first_url
        assert "/league/461.l.100/teams" in second_url
        for call in http.get.call_args_list:
            assert call.kwargs["headers"] == {"Authorization": "Bearer access-tok"}

    def test_league_not_in_account_raises(self):
        leagues = _user_leagues_payload([("461", _league_meta("461.l.100", "100"))])
        http = _http_returning(leagues)

        with pytest.raises(YahooLeagueNotFound):
            fetch_yahoo_members("access-tok", "999", http=http)
        # Never fetched teams for a league that isn't the caller's.
        assert http.get.call_count == 1
